#!/usr/bin/env python3
"""
Monitor web del programador de GeoVictoria: lectura, más botones para iniciar, detener y reiniciar
el programador (solo desde el propio servidor y nunca en mitad de un marcaje sin confirmación).

Uso:
  python scripts/monitor.py                                  # http://127.0.0.1:8765, solo este equipo
  python scripts/monitor.py --abrir                          # además abre el navegador
  python scripts/monitor.py --host 0.0.0.0 --token CLAVE     # accesible por la red, protegido por token
                                                             # (entra con http://SERVIDOR:8765/?t=CLAVE)

Solo LEE archivos (registros, bitácora, latido, alertas): no abre el portal, no modifica datos y no
envía usuarios ni contraseñas (los empleados se reducen a id, nombre, activo y horario). Las alertas
son locales: banda roja, título de la pestaña y, si lo activas, un sonido en esta página.
"""
import argparse
import json
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import bitacora, control_programador
from src.control_concurrencia import desactivar_seleccion_consola
from src import diagnostico_login as dl
from src import estado_monitor
from src.festivos_colombia import es_festivo

PUERTO = 8765
_LOCALES = ("127.0.0.1", "localhost", "::1")


# --- Lectura de datos (todo solo lectura) ------------------------------------

def contar_instancias() -> Optional[int]:
    """Instancias del programador (el lanzador del venv y su intérprete cuentan como una)."""
    try:
        import psutil
    except ImportError:
        return None
    procesos = {}
    for p in psutil.process_iter(["pid", "ppid", "name", "cmdline"]):
        try:
            if (p.info["name"] or "").lower().startswith("python") and "programador.py" in " ".join(p.info["cmdline"] or []):
                procesos[p.info["pid"]] = p.info["ppid"]
        except Exception:
            continue
    return sum(1 for ppid in procesos.values() if ppid not in procesos)


def _sin_credenciales(empleados: List[Dict]) -> List[Dict]:
    """Solo lo necesario para el monitor: jamás usuario ni contraseña."""
    return [{"id": e.get("id"), "nombre": e.get("nombre"), "activo": e.get("activo", True),
             "horario": e.get("horario") or {}} for e in empleados]


_ULTIMO_BUENO: Dict[str, Dict] = {}


def _leer_registros(empleados: List[Dict]) -> Dict[str, Dict]:
    """El programador escribe el registro sin atomicidad: si se lee a mitad de escritura el JSON queda
    truncado. Se reintenta y, si sigue ilegible, se conserva la última lectura válida (así un registro
    a medio escribir no se confunde con "sin marcaje" ni dispara una alarma falsa)."""
    registros = {}
    for e in empleados:
        ruta = bitacora.LOG_DIR / ("registro_ejecuciones.json" if e["id"] == "default" else f"registro_{e['id']}.json")
        for _ in range(3):
            try:
                _ULTIMO_BUENO[e["id"]] = json.loads(ruta.read_text(encoding="utf-8"))
                break
            except FileNotFoundError:
                _ULTIMO_BUENO[e["id"]] = {}
                break
            except (OSError, ValueError):
                time.sleep(0.05)
        registros[e["id"]] = _ULTIMO_BUENO.get(e["id"], {})
    return registros


def _leer_alertas_hoy(hoy_iso: str) -> List[Dict]:
    alertas = []
    try:
        with open(bitacora.LOG_DIR / "alertas.log", "r", encoding="utf-8", errors="replace") as f:
            for linea in f:
                partes = [p.strip() for p in linea.split("|")]
                if len(partes) >= 4 and partes[0].startswith(hoy_iso):
                    alertas.append({"ts": partes[0], "nombre": partes[2], "tipo": partes[3]})
    except OSError:
        pass
    return alertas


def leer_estado(ruta_empleados: Optional[Path] = None, ahora: Optional[datetime] = None) -> Dict:
    """Lee los archivos y calcula el estado del día. Nunca lanza por datos faltantes."""
    ahora = ahora or datetime.now()
    try:
        empleados = _sin_credenciales(dl.leer_empleados(ruta_empleados) if ruta_empleados else dl.leer_empleados())
    except (ValueError, OSError) as e:
        return {"error": f"No se pudo leer la lista de empleados: {e}"}
    hoy = ahora.date()
    return estado_monitor.calcular_estado(
        ahora, empleados, _leer_registros(empleados),
        bitacora.leer_eventos(ahora.strftime("%Y%m%d")), bitacora.leer_latido(),
        alertas_hoy=_leer_alertas_hoy(hoy.isoformat()), instancias=contar_instancias(),
        festivo=es_festivo(hoy),
    )


_LOGS_VISIBLES = {"programador": "programador", "geovictoria": "geovictoria"}
_COLA_LOG = 256 * 1024  # solo se lee el final del archivo, aunque el log pese varios MB


def _secretos(ruta_empleados: Optional[Path] = None) -> List[str]:
    """Usuarios y contraseñas configurados: solo para censurar el log, jamás se envían."""
    try:
        empleados = dl.leer_empleados(ruta_empleados) if ruta_empleados else dl.leer_empleados()
    except (ValueError, OSError):
        return []
    return [str(e[k]) for e in empleados for k in ("usuario", "password") if e.get(k)]


def leer_log(nombre: str, cuantas: int = 150, ruta_empleados: Optional[Path] = None,
             ahora: Optional[datetime] = None) -> Dict:
    """Últimas líneas del log de hoy ("programador" o "geovictoria"), con usuarios y claves censurados.

    Solo acepta esos dos nombres (nada de rutas libres) y nunca lanza por un archivo ausente.
    """
    if nombre not in _LOGS_VISIBLES:
        return {"error": "log desconocido", "lineas": []}
    cuantas = max(20, min(int(cuantas), 500))
    ruta = bitacora.LOG_DIR / f"{_LOGS_VISIBLES[nombre]}_{(ahora or datetime.now()).strftime('%Y%m%d')}.log"
    try:
        with open(ruta, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - _COLA_LOG))
            texto = f.read().decode("utf-8", errors="replace")
    except OSError:
        return {"archivo": ruta.name, "lineas": []}
    return {"archivo": ruta.name, "lineas": estado_monitor.ultimas_lineas_censuradas(texto, cuantas, _secretos(ruta_empleados))}


# --- Control del programador (única parte que actúa; nunca toca el portal) ----------

RAIZ = Path(__file__).resolve().parent.parent
ACCIONES = ("iniciar", "detener", "reiniciar")
_LOOPBACK = ("127.0.0.1", "::1", "::ffff:127.0.0.1")


def ejecutar_accion(accion: str, raiz: Path = RAIZ) -> str:
    """Inicia, detiene o reinicia el programador y devuelve un mensaje. Lanza RuntimeError si falla."""
    if accion in ("detener", "reiniciar"):
        cerrados = control_programador.detener()
    if accion == "detener":
        return f"Programador detenido ({cerrados} proceso(s))." if cerrados else "No había ningún programador en ejecución."
    if accion == "iniciar" and control_programador.procesos_programador():
        raise RuntimeError("Ya hay un programador en ejecución.")
    control_programador.iniciar(raiz)
    if not control_programador.esperar_arranque():
        raise RuntimeError("El programador no aparece tras arrancarlo: revisa el log del programador.")
    return "Programador reiniciado." if accion == "reiniciar" else "Programador iniciado."


# --- Servidor ------------------------------------------------------------------

class Monitor(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, direccion, token: Optional[str], ruta_empleados: Optional[Path] = None):
        super().__init__(direccion, Manejador)
        self.token = token
        self.ruta_empleados = ruta_empleados
        self.raiz = RAIZ
        self._cache: Dict = {"t": 0.0, "dato": {}, "cuerpo": b""}
        self._candado = threading.Lock()
        self.accion_en_curso = threading.Lock()  # una sola acción de control a la vez

    def estado(self):
        """(dict, json) del estado. Una lectura cada 2 s como máximo, aunque haya varias pestañas abiertas."""
        with self._candado:
            if time.monotonic() - self._cache["t"] > 2:
                dato = leer_estado(self.ruta_empleados)
                self._cache.update(dato=dato, cuerpo=json.dumps(dato, ensure_ascii=False).encode("utf-8"),
                                   t=time.monotonic())
            return self._cache["dato"], self._cache["cuerpo"]

    def estado_json(self) -> bytes:
        return self.estado()[1]

    def invalidar_estado(self) -> None:
        with self._candado:
            self._cache["t"] = 0.0


class Manejador(BaseHTTPRequestHandler):
    server: Monitor

    def log_message(self, *args):  # sin ruido en consola
        pass

    def _responder(self, codigo: int, cuerpo: bytes, tipo: str = "text/html; charset=utf-8") -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _autorizado(self, consulta: Dict) -> bool:
        if not self.server.token:
            return True
        enviado = (consulta.get("t") or [self.headers.get("X-Token", "")])[0]
        return enviado == self.server.token

    def _es_local(self) -> bool:
        return self.client_address[0] in _LOOPBACK

    def _json(self, codigo: int, cuerpo: Dict) -> None:
        self._responder(codigo, json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_POST(self):
        """Única ruta que actúa: /api/accion. Solo desde este equipo, con token si lo hay, con cabecera
        propia (un formulario de otra web no puede enviarla) y sin reiniciar a mitad de un marcaje."""
        url = urlparse(self.path)
        if url.path != "/api/accion":
            return self._json(404, {"ok": False, "mensaje": "No encontrado"})
        if not self._es_local():
            return self._json(403, {"ok": False, "mensaje": "Las acciones solo se permiten desde el propio servidor."})
        if not self._autorizado(parse_qs(url.query)):
            return self._json(401, {"ok": False, "mensaje": "Falta el token."})
        origen = self.headers.get("Origin")
        if self.headers.get("X-GeoVic-Accion") != "1" or (origen and urlparse(origen).netloc != self.headers.get("Host")):
            return self._json(403, {"ok": False, "mensaje": "Petición no válida."})
        try:
            largo = int(self.headers.get("Content-Length") or 0)
            datos = json.loads(self.rfile.read(min(largo, 1024)) or b"{}")
            accion, forzar = datos.get("accion"), bool(datos.get("forzar"))
        except (ValueError, AttributeError):
            return self._json(400, {"ok": False, "mensaje": "Cuerpo no válido."})
        if accion not in ACCIONES:
            return self._json(400, {"ok": False, "mensaje": "Acción desconocida."})

        if not self.server.accion_en_curso.acquire(blocking=False):
            return self._json(409, {"ok": False, "mensaje": "Ya hay una acción en curso."})
        try:
            estado, _ = self.server.estado()
            bloqueo = None if accion == "iniciar" else estado_monitor.bloqueo_por_marcaje(estado, datetime.now())
            if bloqueo and not forzar:
                return self._json(409, {"ok": False, "bloqueado": bloqueo,
                                        "mensaje": f"Hay un marcaje en curso o a punto de ejecutarse ({bloqueo})."})
            try:
                mensaje = ejecutar_accion(accion, self.server.raiz)
                bitacora.registrar("control", accion=accion, forzado=bool(bloqueo), ok=True)
                resultado = (200, {"ok": True, "mensaje": mensaje})
            except Exception as e:
                bitacora.registrar("control", accion=accion, forzado=bool(bloqueo), ok=False, error=str(e))
                resultado = (500, {"ok": False, "mensaje": str(e)})
            self.server.invalidar_estado()
            return self._json(*resultado)
        finally:
            self.server.accion_en_curso.release()

    def do_GET(self):
        url = urlparse(self.path)
        if not self._autorizado(parse_qs(url.query)):
            self._responder(401, "<h1>401</h1><p>Falta el token: abre la página con <code>?t=TOKEN</code>.</p>".encode("utf-8"))
        elif url.path == "/":
            self._responder(200, PAGINA.encode("utf-8"))
        elif url.path == "/api/estado":
            self._responder(200, self.server.estado_json(), "application/json; charset=utf-8")
        elif url.path == "/api/control":
            estado, _ = self.server.estado()
            cuerpo = {"permitido": self._es_local(), "bloqueo": estado_monitor.bloqueo_por_marcaje(estado, datetime.now())}
            self._responder(200, json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        elif url.path == "/api/log":
            consulta = parse_qs(url.query)
            try:
                cuantas = int((consulta.get("n") or ["150"])[0])
            except ValueError:
                cuantas = 150
            cuerpo = leer_log((consulta.get("f") or ["programador"])[0], cuantas, self.server.ruta_empleados)
            self._responder(200, json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        else:
            self._responder(404, b"No encontrado", "text/plain; charset=utf-8")


PAGINA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GeoVic · Monitor</title>
<style>
:root{--bg:#f4f6f8;--card:#fff;--tx:#1b2430;--mut:#6b7684;--bd:#dde3ea;--ok:#1a7f45;--okb:#e3f5ea;--av:#8a5a00;--avb:#fff1d6;--cr:#b3261e;--crb:#fde4e2;--pe:#455a7a;--peb:#e8eef7}
@media (prefers-color-scheme:dark){:root{--bg:#10151c;--card:#18202a;--tx:#e6ebf1;--mut:#93a0b0;--bd:#2a3542;--ok:#5ad08a;--okb:#14301f;--av:#f0b550;--avb:#3a2c0e;--cr:#ff8f87;--crb:#40191a;--pe:#9db4d6;--peb:#1e2a3b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:18px 20px;border-bottom:1px solid var(--bd)}header.ok{background:var(--okb)}header.aviso{background:var(--avb)}header.critico{background:var(--crb)}
h1{margin:0;font-size:22px}.sub{color:var(--mut);font-size:13px;margin-top:2px}
main{max-width:1180px;margin:0 auto;padding:16px 20px 40px;display:grid;gap:16px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px 16px}
.card h2{margin:0 0 10px;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
.msgs{margin:8px 0 0;padding:0;list-style:none;display:grid;gap:4px}.msgs li{padding:6px 10px;border-radius:6px;font-weight:600}
.msgs .critico{background:var(--crb);color:var(--cr)}.msgs .aviso{background:var(--avb);color:var(--av)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.kv b{display:block;font-size:12px;color:var(--mut);font-weight:500}.kv span{font-size:17px;font-weight:650}
.chips{display:flex;gap:8px;flex-wrap:wrap}.chip{padding:3px 10px;border-radius:99px;font-size:13px;font-weight:600}
table{width:100%;border-collapse:collapse}th{font-size:12px;color:var(--mut);font-weight:600;text-align:left;padding:6px 8px;border-bottom:1px solid var(--bd)}
td{padding:8px;border-bottom:1px solid var(--bd);vertical-align:top}tr:last-child td{border-bottom:0}.wrap{overflow-x:auto}
.b{display:inline-block;padding:2px 9px;border-radius:99px;font-size:12.5px;font-weight:700;white-space:nowrap}
.confirmada{background:var(--okb);color:var(--ok)}.marcada{background:var(--okb);color:var(--ok);opacity:.85}.pendiente{background:var(--peb);color:var(--pe)}
.vencida,.no_confirmada{background:var(--crb);color:var(--cr)}.na{color:var(--mut)}.small{font-size:12px;color:var(--mut)}
.f-crit td:first-child{box-shadow:inset 4px 0 0 var(--cr)}.dup{color:var(--av);font-weight:700}
ul.act{list-style:none;margin:0;padding:0;max-height:330px;overflow:auto}ul.act li{padding:4px 0;border-bottom:1px solid var(--bd);display:flex;gap:10px;font-size:13.5px}
ul.act .h{color:var(--mut);min-width:62px}ul.act .n{min-width:150px;font-weight:600}.error{color:var(--cr)}.aviso{color:var(--av)}
[hidden]{display:none!important}
pre.log{margin:0;max-height:380px;overflow:auto;font:12.5px/1.4 ui-monospace,Consolas,monospace;white-space:pre-wrap;word-break:break-word;background:var(--bg);border:1px solid var(--bd);border-radius:8px;padding:8px}
pre.log .e{color:var(--cr);font-weight:600}pre.log .w{color:var(--av)}summary{cursor:pointer}
button{font:inherit;padding:5px 12px;border-radius:8px;border:1px solid var(--bd);background:var(--card);color:var(--tx);cursor:pointer}
</style></head><body>
<header id="cab" class="ok"><h1 id="titulo">Cargando…</h1><div class="sub" id="sub"></div><ul class="msgs" id="msgs"></ul></header>
<main>
 <section class="card"><h2>Programador</h2><div class="grid" id="prog"></div>
  <div id="ctl" hidden style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
   <button id="b-reiniciar">↻ Reiniciar</button><button id="b-detener">■ Detener</button><button id="b-iniciar">▶ Iniciar</button>
   <span class="small" id="ctlmsg"></span></div></section>
 <section class="card"><h2>Resumen del día</h2><div id="resumen"></div></section>
 <section class="card"><h2>Empleados</h2><div class="wrap"><table><thead><tr><th>Empleado</th><th>Entrada</th><th>Salida</th><th>Último login</th></tr></thead><tbody id="filas"></tbody></table></div></section>
 <section class="card"><h2>Actividad reciente</h2><ul class="act" id="act"></ul></section>
 <section class="card"><details id="logbox"><summary><b>Log en vivo</b> <span class="small">(reemplaza la ventana "Log en vivo"; usuarios y claves ocultos)</span></summary>
  <div class="small" style="margin:8px 0"><select id="logsel"><option value="programador">programador</option><option value="geovictoria">geovictoria (navegador)</option></select>
   <label><input type="checkbox" id="logsolo"> solo avisos y errores</label> <span id="logarch"></span></div>
  <pre id="logtxt" class="log">Abre este panel para ver el log.</pre></details></section>
 <div class="small">Solo lectura (salvo los botones del programador, solo desde este equipo) · se actualiza cada 5 s · <span id="ult"></span> · <button id="snd">🔔 Sonido: apagado</button></div>
</main>
<script>
const Q = new URLSearchParams(location.search), T = Q.get("t");
const URL_API = "/api/estado" + (T ? "?t=" + encodeURIComponent(T) : "");
const E = {pendiente:"⏳ Pendiente", marcada:"✔ Marcada", confirmada:"✔✔ Confirmada", no_confirmada:"⚠ NO confirmada", vencida:"✖ VENCIDA"};
const NIV = {ok:"🟢 Todo en orden", aviso:"🟡 Atención", critico:"🔴 CRÍTICO"};
let sonido = false, ultimoNivel = "ok", ctx = null;
const el = (t, c, x) => { const n = document.createElement(t); if (c) n.className = c; if (x !== undefined) n.textContent = x; return n; };
function pitar(){ try{ ctx = ctx || new (window.AudioContext||window.webkitAudioContext)(); const o=ctx.createOscillator(), g=ctx.createGain(); o.connect(g); g.connect(ctx.destination); o.frequency.value=880; g.gain.value=.15; o.start(); o.stop(ctx.currentTime+.4);}catch(e){} }
document.getElementById("snd").onclick = (ev) => { sonido = !sonido; ev.target.textContent = "🔔 Sonido: " + (sonido ? "encendido" : "apagado"); if (sonido) pitar(); };
function celda(a){
  const td = el("td");
  if (!a) { td.append(el("span","na","—")); return td; }
  td.append(el("span","b "+a.estado, E[a.estado] || a.estado));
  if (a.duplicada) td.append(" ", el("span","dup","×"+a.exitos+" duplicada"));
  const l = el("div","small"); let t = "programada " + (a.programada || "?");
  if (a.hora) t += " · marcó " + a.hora + (a.origen === "portal" ? " (detectada en el portal)" : "");
  if (a.detalle) t += " · " + a.detalle;
  l.textContent = t; td.append(l); return td;
}
function pintar(d){
  if (d.error){ document.getElementById("titulo").textContent = "Error: " + d.error; return; }
  const cab = document.getElementById("cab"); cab.className = d.nivel;
  document.getElementById("titulo").textContent = NIV[d.nivel];
  document.getElementById("sub").textContent = new Date(d.ahora).toLocaleString("es-CO");
  const ms = document.getElementById("msgs"); ms.replaceChildren();
  d.mensajes.forEach(m => ms.append(el("li", m.nivel, m.texto)));
  document.title = (d.nivel === "critico" ? "🔴 " : d.nivel === "aviso" ? "🟡 " : "🟢 ") + "GeoVic · Monitor";
  if (d.nivel === "critico" && ultimoNivel !== "critico" && sonido) pitar();
  ultimoNivel = d.nivel;

  const p = d.programador, g = document.getElementById("prog"); g.replaceChildren();
  const kv = (k, v, c) => { const x = el("div","kv"); x.append(el("b","",k), el("span", c || "", v)); g.append(x); };
  kv("Estado", p.vivo ? "🟢 Vivo" : "🔴 Sin latido", p.vivo ? "" : "error");
  kv("Último latido", p.edad_seg === null ? "—" : "hace " + p.edad_seg + " s");
  kv("Scheduler", p.scheduler_ok === true ? "✔ responde" : p.scheduler_ok === false ? "✖ NO responde" : (p.fase || "—"), p.scheduler_ok === false ? "error" : "");
  kv("Instancias", p.instancias === null ? "?" : String(p.instancias), p.instancias > 1 ? "aviso" : "");
  kv("PID", p.pid || "—"); kv("Arranques hoy", String(p.arranques_hoy));

  const r = document.getElementById("resumen"); r.replaceChildren();
  ["entrada","salida"].forEach(k => {
    const fila = el("div","chips"); fila.style.marginBottom = "6px"; fila.append(el("b","", (k === "entrada" ? "Entradas" : "Salidas") + " (" + d.resumen.empleados + "): "));
    Object.entries(d.resumen[k]).forEach(([e,n]) => fila.append(el("span","chip "+e, n + " " + (E[e]||e).replace(/^\S+\s/,""))));
    r.append(fila);
  });
  r.append(el("div","small","Alertas hoy: " + d.alertas.total + (d.alertas.total ? " · " + Object.entries(d.alertas.por_usuario).map(([n,c]) => n + " " + c).join(", ") : "")));

  const rank = f => f.entrada && (f.entrada.estado === "vencida" || f.entrada.estado === "no_confirmada") ? 0 : 1;
  const filas = [...d.empleados].sort((a,b) => rank(a) - rank(b) || String(a.entrada&&a.entrada.programada).localeCompare(String(b.entrada&&b.entrada.programada)));
  const tb = document.getElementById("filas"); tb.replaceChildren();
  filas.forEach(f => {
    const tr = el("tr", f.entrada && (f.entrada.estado==="vencida"||f.entrada.estado==="no_confirmada") ? "f-crit" : "");
    const t1 = el("td"); t1.append(el("b","",f.nombre)); t1.append(el("div","small", f.dia === "desactivado" ? "desactivado" : f.dia));
    tr.append(t1, celda(f.entrada), celda(f.salida));
    const tl = el("td");
    if (f.login) { tl.append(el("span", f.login.ok ? "" : "error", (f.login.ok ? "✔ " : "✖ ") + f.login.hora + (f.login.ok ? "" : " " + (f.login.motivo || ""))));
      if (f.fallos_login) tl.append(el("div","small", f.fallos_login + " fallo(s) hoy")); } else tl.append(el("span","na","sin eventos"));
    tr.append(tl); tb.append(tr);
  });

  const a = document.getElementById("act"); a.replaceChildren();
  d.actividad.forEach(x => { const li = el("li", x.nivel); li.append(el("span","h",x.hora), el("span","n",x.nombre), el("span","",x.texto)); a.append(li); });
  document.getElementById("ult").textContent = "última lectura " + new Date().toLocaleTimeString("es-CO");
}
async function ciclo(){
  try { const r = await fetch(URL_API, {cache:"no-store"}); if (r.status === 401) { document.getElementById("titulo").textContent = "Falta el token en la URL (?t=…)"; return; } pintar(await r.json()); }
  catch(e){ document.getElementById("titulo").textContent = "Sin conexión con el monitor"; document.getElementById("cab").className = "critico"; }
}
const TXT = {reiniciar:"reiniciar", detener:"DETENER (no marcará nada hasta que lo inicies)", iniciar:"iniciar"};
async function accion(nombre, forzar){
  const msg = document.getElementById("ctlmsg"), botones = [...document.querySelectorAll("#ctl button")];
  botones.forEach(b => b.disabled = true); msg.textContent = "Trabajando… (puede tardar unos segundos)";
  try {
    const r = await fetch("/api/accion" + (T ? "?t=" + encodeURIComponent(T) : ""), {method:"POST",
      headers:{"Content-Type":"application/json","X-GeoVic-Accion":"1"}, body: JSON.stringify({accion:nombre, forzar:!!forzar})});
    const d = await r.json();
    if (r.status === 409 && d.bloqueado && !forzar) {
      msg.textContent = "";
      if (confirm(d.mensaje + "\n\nReiniciar ahora puede dejar ese marcaje a medias o sin confirmar.\n¿Hacerlo de todos modos?")) return accion(nombre, true);
    } else msg.textContent = (d.ok ? "✔ " : "✖ ") + d.mensaje;
  } catch(e){ msg.textContent = "✖ No se pudo contactar con el monitor."; }
  botones.forEach(b => b.disabled = false); ciclo();
}
for (const n of ["reiniciar","detener","iniciar"]) document.getElementById("b-"+n).onclick = () => { if (confirm("¿Seguro que quieres " + TXT[n] + " el programador?")) accion(n, false); };
async function cicloControl(){
  try {
    const r = await fetch("/api/control" + (T ? "?t=" + encodeURIComponent(T) : ""), {cache:"no-store"}); const d = await r.json();
    const caja = document.getElementById("ctl"); caja.hidden = !d.permitido;
    ["reiniciar","detener"].forEach(n => document.getElementById("b-"+n).title = d.bloqueo ? "Ahora no conviene: " + d.bloqueo : "");
  } catch(e){}
}
async function cicloLog(){
  const caja = document.getElementById("logbox"); if (!caja.open) return;
  const pre = document.getElementById("logtxt");
  try {
    const f = document.getElementById("logsel").value;
    const r = await fetch("/api/log?f=" + f + "&n=300" + (T ? "&t=" + encodeURIComponent(T) : ""), {cache:"no-store"});
    const d = await r.json(); const solo = document.getElementById("logsolo").checked;
    const abajo = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 30;
    pre.replaceChildren();
    d.lineas.filter(l => !solo || /ERROR|WARNING|❌|⚠/.test(l)).forEach(l => {
      pre.append(el("div", /ERROR|❌/.test(l) ? "e" : /WARNING|⚠/.test(l) ? "w" : "", l));
    });
    if (!pre.childNodes.length) pre.textContent = "Sin líneas todavía hoy.";
    if (abajo) pre.scrollTop = pre.scrollHeight;
    document.getElementById("logarch").textContent = d.archivo || "";
  } catch(e){ pre.textContent = "No se pudo leer el log."; }
}
document.getElementById("logbox").addEventListener("toggle", cicloLog);
document.getElementById("logsel").onchange = cicloLog; document.getElementById("logsolo").onchange = cicloLog;
ciclo(); setInterval(ciclo, 5000); setInterval(cicloLog, 5000); cicloControl(); setInterval(cicloControl, 5000);
</script></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor web de solo lectura del programador.")
    parser.add_argument("--host", default="127.0.0.1", help="dirección donde escuchar (por defecto solo este equipo)")
    parser.add_argument("--puerto", type=int, default=PUERTO)
    parser.add_argument("--token", help="obligatorio si --host no es local")
    parser.add_argument("--empleados", help="ruta de employees.json (para pruebas)")
    parser.add_argument("--abrir", action="store_true", help="abrir el navegador")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    desactivar_seleccion_consola()  # un clic en la ventana no debe congelar el monitor

    if args.host not in _LOCALES and not args.token:
        print("❌ Para escuchar en la red hay que indicar --token (la página muestra nombres y horarios del personal).")
        return 2

    try:
        servidor = Monitor((args.host, args.puerto), args.token, Path(args.empleados) if args.empleados else None)
    except OSError as e:
        print(f"❌ No se pudo abrir el puerto {args.puerto}: {e}\n   ¿Ya hay un monitor abierto? Usa --puerto OTRO.")
        return 1

    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '') else args.host}:{args.puerto}/" + (f"?t={args.token}" if args.token else "")
    contar_instancias()  # la primera lectura de procesos tarda varios segundos en Windows; así la página abre al instante
    print(f"✅ Monitor en {url}   (Ctrl+C para cerrar; solo lectura)")
    if args.abrir:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nMonitor cerrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
