#!/usr/bin/env python3
"""
Monitor web del programador de GeoVictoria: lectura, más botones para iniciar, detener y reiniciar
el programador (solo desde el propio servidor y nunca en mitad de un marcaje sin confirmación).

Uso:
  python scripts/monitor.py                                  # http://127.0.0.1:8765, solo este equipo
  python scripts/monitor.py --abrir                          # además abre el navegador
  python scripts/monitor.py --host 0.0.0.0 --token CLAVE     # accesible por la red, protegido por token
                                                             # (entra con http://SERVIDOR:8765/?t=CLAVE)

Lee archivos (registros, bitácora, latido, alertas) y no abre el portal ni envía usuarios o
contraseñas (los empleados se reducen a id, nombre, activo y horario). Lo único que escribe es
config/novedades.json (vacaciones, desactivar, retiro; sin credenciales), y solo desde este equipo.
Las alertas son locales: banda roja, título de la pestaña y, si lo activas, un sonido en esta página.
"""
import argparse
import hmac
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

from src import bitacora, control_programador, credenciales, novedades
from src import empleados as empleados_mod
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
             "horario": e.get("horario") or {}, "ausencias": e.get("ausencias") or []} for e in empleados]


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


def _ruta_novedades(ruta_empleados: Optional[Path]) -> Path:
    """config/novedades.json, junto al employees.json en uso (en los tests, uno temporal)."""
    return novedades.ruta_novedades(ruta_empleados or empleados_mod.EMPLOYEES_FILE)


def _notas_reemplazo(todos: List[Dict], hoy) -> Dict[str, str]:
    """Texto por empleado: "reemplaza a Ana (01/12 → 05/12)" y "cubierto por Pedro (…)" mientras no termine."""
    ids = [e.get("id") for e in todos]
    nombres = {e.get("id"): e.get("nombre") for e in todos}
    notas: Dict[str, str] = {}
    for e in todos:
        r = empleados_mod.reemplazo_de(e, ids)
        if not r or "invalido" in r or r["hasta"] < hoy:
            continue
        rango = f"{r['desde'].strftime('%d/%m/%Y')} → {r['hasta'].strftime('%d/%m/%Y')}"
        notas[e.get("id")] = f"reemplaza a {nombres.get(r['cubre_a'])} ({rango})"
        notas[r["cubre_a"]] = f"cubierto por {e.get('nombre')} ({rango})"
    return notas


def leer_estado(ruta_empleados: Optional[Path] = None, ahora: Optional[datetime] = None) -> Dict:
    """Lee los archivos y calcula el estado del día. Nunca lanza por datos faltantes."""
    ahora = ahora or datetime.now()
    try:
        crudos = dl.leer_empleados(ruta_empleados) if ruta_empleados else dl.leer_empleados()
    except (ValueError, OSError) as e:
        return {"error": f"No se pudo leer la lista de empleados: {e}"}
    # Reemplazos temporales: horario de quien cubren + ausencias deducidas (fuera de periodo / cubierto)
    empleados = _sin_credenciales(empleados_mod.resolver_reemplazos(crudos))
    hoy = ahora.date()
    lista_nov, error_nov = novedades.leer(_ruta_novedades(ruta_empleados))
    # Las novedades del monitor cuentan como ausencias: así "Ausentes hoy", VENCIDA y "Marcar pendientes"
    # las respetan igual que las escritas a mano en employees.json.
    con_novedades = [novedades.combinar(e, lista_nov) for e in empleados]
    estado = estado_monitor.calcular_estado(
        ahora, con_novedades, _leer_registros(empleados),
        bitacora.leer_eventos(ahora.strftime("%Y%m%d")), bitacora.leer_latido(),
        alertas_hoy=_leer_alertas_hoy(hoy.isoformat()), instancias=contar_instancias(),
        festivo=es_festivo(hoy),
    )
    notas = _notas_reemplazo(crudos, hoy)
    for fila in estado.get("empleados", []):
        fila["novedades"] = novedades.vigentes_o_futuras(lista_nov, fila.get("id"), hoy)
        fila["reemplazo"] = notas.get(fila.get("id"))
    for emp_mal, motivo in empleados_mod.reemplazos_invalidos(crudos):
        estado["mensajes"].append({"nivel": "aviso", "texto": f"{emp_mal.get('nombre')}: reemplazo mal configurado "
                                                               f"en employees.json ({motivo}); no se le marca"})
        if estado.get("nivel") == "ok":
            estado["nivel"] = "aviso"
    if error_nov:
        estado["mensajes"].insert(0, {"nivel": "critico", "texto": f"{error_nov}. Si el programador se reinicia así, "
                                                                     "NO aplicará vacaciones ni desactivaciones."})
        estado["nivel"] = "critico"
    return estado


_LOGS_VISIBLES = {"programador": "programador", "geovictoria": "geovictoria"}
_COLA_LOG = 256 * 1024  # solo se lee el final del archivo, aunque el log pese varios MB


def _secretos(ruta_empleados: Optional[Path] = None) -> List[str]:
    """Usuarios y contraseñas configurados: solo para censurar el log, jamás se envían."""
    try:
        empleados = dl.leer_empleados(ruta_empleados) if ruta_empleados else dl.leer_empleados()
    except (ValueError, OSError):
        return []
    secretos = []
    for e in empleados:
        secretos += [str(e[k]) for k in ("usuario", "password") if e.get(k)]
        if credenciales.esta_cifrada(e.get("password")):  # lo que podría salir en un log es la contraseña en claro
            try:
                secretos.append(credenciales.revelar(e["password"]))
            except ValueError:
                pass
    return secretos


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
ACCIONES = ("iniciar", "detener", "reiniciar", "marcar_pendientes", "novedad")
_LOOPBACK = ("127.0.0.1", "::1", "::ffff:127.0.0.1")
_HOSTS_LOCALES = ("127.0.0.1", "localhost", "::1")


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
        return hmac.compare_digest(enviado.encode("utf-8"), self.server.token.encode("utf-8"))

    def _es_local(self) -> bool:
        return self.client_address[0] in _LOOPBACK

    def _host_valido(self) -> bool:
        """Defensa contra DNS rebinding: una web maliciosa abierta en este equipo puede hacer que SU dominio
        resuelva a 127.0.0.1; la petición sale de aquí, con la cabecera propia y Origin == Host, así que
        solo el Host la delata. Sin token se exige un Host local; con token (modo red) el token basta."""
        if self.server.token:
            return True
        try:
            nombre = urlparse("//" + (self.headers.get("Host") or "")).hostname
        except ValueError:
            return False
        return nombre in _HOSTS_LOCALES

    def _json(self, codigo: int, cuerpo: Dict) -> None:
        self._responder(codigo, json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _no_permitido(self):
        """PUT, DELETE y PATCH no existen: se lee el cuerpo (ver do_POST) y se contesta 405."""
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = 0
        if largo > 0:
            self.rfile.read(min(largo, 1024))
        if largo > 1024:
            self.close_connection = True
        self._responder(405, b"Metodo no permitido", "text/plain; charset=utf-8")

    do_PUT = do_DELETE = do_PATCH = _no_permitido

    def _marcar_pendientes(self, estado: Dict) -> None:
        """Lanza el marcado de los pendientes (vencidos o contradichos por el portal) en segundo plano.

        La lista se recalcula aquí con el estado del servidor: no se confía en lo que muestre la página.
        Quien marca (scripts/marcar_pendientes.py) vuelve a comprobar el portal antes de cada clic.
        """
        pendientes = estado_monitor.pendientes_de_marcar(estado)
        if not pendientes:
            return self._json(200, {"ok": True, "mensaje": "No hay marcajes pendientes."})
        try:
            control_programador.lanzar_marcado(self.server.raiz, pendientes)
        except Exception as e:
            bitacora.registrar("control", accion="marcar_pendientes", ok=False, error=str(e))
            return self._json(500, {"ok": False, "mensaje": f"No se pudo iniciar el marcado: {e}"})
        bitacora.registrar("control", accion="marcar_pendientes", ok=True, pendientes=len(pendientes))
        self.server.invalidar_estado()
        nombres = ", ".join(f"{p['nombre']} ({p['accion']})" for p in pendientes)
        self._json(200, {"ok": True, "mensaje": f"Marcando {len(pendientes)} pendiente(s): {nombres}. "
                                                "El estado se actualiza en 1 o 2 minutos."})

    def _novedad(self, datos: Dict, estado: Dict, forzar: bool) -> None:
        """Agrega o quita una novedad (vacaciones, desactivar, retiro) en config/novedades.json.

        Nunca toca employees.json (credenciales). Lo que afecta a HOY exige confirmar (forzar):
        desactivar a quien ya marcó entrada deja su salida sin marcar, y reactivar a quien ya pasó su
        hora hace que el programador marque la entrada en su revisión horaria.
        """
        ruta = _ruta_novedades(self.server.ruta_empleados)
        hoy = datetime.now().date()
        filas = {f.get("id"): f for f in estado.get("empleados", [])}
        op = datos.get("op")
        try:
            if op == "agregar":
                nueva = novedades.construir(datos, list(filas), hoy)
                fila = filas.get(nueva["emp_id"]) or {}
                entrada, salida = fila.get("entrada") or {}, fila.get("salida") or {}
                if (novedades.afecta_hoy(nueva, hoy) and entrada.get("hora") and not salida.get("hora")
                        and not forzar):
                    return self._json(409, {"ok": False, "bloqueado": "entrada ya marcada",
                                            "mensaje": f"{fila.get('nombre')} ya marcó entrada hoy ({entrada['hora']}): "
                                                       "si guardas ahora, NO se marcará su salida de hoy."})
                novedades.agregar(ruta, nueva)
                emp, como = {"id": nueva["emp_id"], "nombre": fila.get("nombre")}, "agregada"
                afectada = nueva
            elif op == "terminar":
                actuales, _ = novedades.leer(ruta)
                objetivo = next((n for n in actuales if n.get("id") == datos.get("id")), None)
                if objetivo and novedades.afecta_hoy(objetivo, hoy) and not forzar:
                    return self._json(409, {"ok": False, "bloqueado": "vuelve hoy",
                                            "mensaje": "Vuelve a marcar desde HOY: si ya pasó su hora de entrada, el "
                                                       "programador la marcará en su próxima revisión horaria (hasta las 12:00)."})
                afectada, como = novedades.terminar(ruta, str(datos.get("id")), hoy)
                emp = {"id": afectada.get("emp_id"), "nombre": (filas.get(afectada.get("emp_id")) or {}).get("nombre")}
            else:
                return self._json(400, {"ok": False, "mensaje": "Operación desconocida."})
        except novedades.NovedadInvalida as e:
            return self._json(400, {"ok": False, "mensaje": str(e)})
        except OSError as e:
            bitacora.registrar("control", accion="novedad", ok=False, error=str(e))
            return self._json(500, {"ok": False, "mensaje": f"No se pudo guardar: {e}"})
        bitacora.registrar("novedad", emp, operacion=como, novedad_id=afectada.get("id"), tipo_novedad=afectada.get("tipo"),
                           desde=afectada.get("desde"), hasta=afectada.get("hasta"), motivo=afectada.get("motivo"),
                           forzado=forzar)
        self.server.invalidar_estado()
        fin = afectada.get("hasta") or "sin fecha de fin"
        texto = {"agregada": f"Guardado: {emp['nombre']} — {afectada.get('motivo')} desde {afectada.get('desde')} ({fin}).",
                 "eliminada": f"Quitada la novedad de {emp['nombre']} ({afectada.get('motivo')}).",
                 "cerrada": f"{emp['nombre']} vuelve a marcar desde hoy ({afectada.get('motivo')} cerrada ayer)."}[como]
        return self._json(200, {"ok": True, "mensaje": texto + " No hace falta reiniciar."})

    def do_POST(self):
        """Única ruta que actúa: /api/accion. Solo desde este equipo, con token si lo hay, con cabecera
        propia (un formulario de otra web no puede enviarla) y sin reiniciar a mitad de un marcaje."""
        url = urlparse(self.path)
        # El cuerpo se lee SIEMPRE, antes de cualquier respuesta: si se contesta (401, 403, 404…) con
        # el cuerpo sin leer, Windows cierra la conexión a lo bruto y el cliente no llega a ver el error.
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = 0
        crudo = self.rfile.read(min(largo, 1024)) if largo > 0 else b""
        if largo > 1024:
            self.close_connection = True  # cuerpo desmesurado: se responde y se cierra
        if not self._host_valido():
            return self._json(403, {"ok": False, "mensaje": "Host no permitido."})
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
            datos = json.loads(crudo or b"{}")
            accion, forzar = datos.get("accion"), bool(datos.get("forzar"))
        except (ValueError, AttributeError):
            return self._json(400, {"ok": False, "mensaje": "Cuerpo no válido."})
        if accion not in ACCIONES:
            return self._json(400, {"ok": False, "mensaje": "Acción desconocida."})

        if not self.server.accion_en_curso.acquire(blocking=False):
            return self._json(409, {"ok": False, "mensaje": "Ya hay una acción en curso."})
        try:
            estado, _ = self.server.estado()
            if accion == "marcar_pendientes":
                return self._marcar_pendientes(estado)
            if accion == "novedad":
                return self._novedad(datos, estado, forzar)
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
        if not self._host_valido():
            self._responder(403, b"Host no permitido", "text/plain; charset=utf-8")
        elif not self._autorizado(parse_qs(url.query)):
            self._responder(401, "<h1>401</h1><p>Falta el token: abre la página con <code>?t=TOKEN</code>.</p>".encode("utf-8"))
        elif url.path == "/":
            self._responder(200, PAGINA.encode("utf-8"))
        elif url.path == "/api/estado":
            self._responder(200, self.server.estado_json(), "application/json; charset=utf-8")
        elif url.path == "/api/control":
            estado, _ = self.server.estado()
            cuerpo = {"permitido": self._es_local(), "bloqueo": estado_monitor.bloqueo_por_marcaje(estado, datetime.now()),
                      "pendientes": [{"nombre": p["nombre"], "accion": p["accion"]}
                                     for p in estado_monitor.pendientes_de_marcar(estado)]}
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
<link id="fav" rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='7' fill='%231a7f45'/%3E%3C/svg%3E">
<style>
/* Estilo IBM Carbon, a partir de design-md/ibm/DESIGN.md de VoltAgent/awesome-design-md: barra superior
   negra, esquinas rectas, sin sombras, cifras grandes en peso 300, tabla con cabecera gris y un único azul
   de acción. Claro = tema White de Carbon; oscuro (si el sistema lo pide) = tema g100. Verde, ámbar y rojo
   son los colores de estado de Carbon y son la información del panel: no usarlos como decoración. */
:root{--bg:#f4f4f4;--card:#ffffff;--sub:#f4f4f4;--tx:#161616;--mut:#525252;--bd:#e0e0e0;--bd2:#e0e0e0;--sh:none;
--ff:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;--ffs:normal;--fs:14px;--fsm:"IBM Plex Mono",Consolas,monospace;--fmono:"IBM Plex Mono",Consolas,monospace;
--ok:#198038;--okb:#a7f0ba;--av:#8e6a00;--avb:#fcf4d6;--cr:#da1e28;--crb:#ffd7d9;--pe:#161616;--peb:#e0e0e0;--pebar:#c6c6c6;
--ac:#0f62fe;--hdbg:#161616;--hdtx:#f4f4f4;--hdmut:#c6c6c6;--hdbd:#393939;--hdpad:10px 20px;--lgbg:#0f62fe;--lgtx:#fff;
--h1s:15px;--h1w:600;--h1ls:.16px;--r:0;--rp:0;--rc:0;--rk:0;--rb:0;--rt:24px;--rbar:0;--gap:16px;--cpad:20px;--cbd:0;
--h2s:20px;--h2w:400;--h2f:inherit;--h2t:none;--h2ls:0;--h2c:#161616;--h2ic:#0f62fe;
--kgap:1px;--kbg:#e0e0e0;--kbd:1px solid #e0e0e0;--klbs:12px;--klbw:400;--klbt:none;--klbls:.32px;--kvs:28px;--kvw:300;--kvls:0;
--bw:400;--bpad:11px 16px;--bbd:#393939;--bbg:#393939;--btx:#fff;--bbgh:#4c4c4c;--pri:#0f62fe;--pritx:#fff;--pelbg:#da1e28;--peltx:#fff;--pelbd:#da1e28;
--barh:8px;--tagpad:2px 10px;--tagw:400;--tagt:none;--tagls:.16px;--ths:14px;--tht:none;--thls:.16px;--thc:#161616;--thbg:#e0e0e0;--thpad:12px 16px;--tdpad:12px 16px;--rowh:#e8e8e8;
--msgbg:#393939;--logbg:#262626;--logtx:#f4f4f4}
@media (prefers-color-scheme:dark){:root{--bg:#161616;--card:#262626;--sub:#393939;--tx:#f4f4f4;--mut:#c6c6c6;--bd:#393939;--bd2:#393939;
--ok:#42be65;--okb:#044317;--av:#f1c21b;--avb:#3d3200;--cr:#ff8389;--crb:#520408;--pe:#f4f4f4;--peb:#4c4c4c;--pebar:#6f6f6f;
--ac:#78a9ff;--hdbg:#000000;--hdbd:#262626;--lgbg:#0f62fe;--h2c:#f4f4f4;--h2ic:#78a9ff;--kbg:#525252;--kbd:1px solid #525252;
--bbd:#6f6f6f;--bbg:#6f6f6f;--bbgh:#5e5e5e;--pri:#0f62fe;--pelbg:#da1e28;--pelbd:#da1e28;
--thc:#f4f4f4;--thbg:#393939;--rowh:#333333;--msgbg:#262626;--logbg:#161616;--logtx:#f4f4f4}}
.estado{font-weight:400}
.card>h2 .ic{display:none}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:var(--fs)/1.5 var(--ff);font-feature-settings:var(--ffs);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.ic{width:1.15em;height:1.15em;flex:none;vertical-align:-.2em;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
header{background:var(--hdbg);color:var(--hdtx);border-bottom:1px solid var(--hdbd)}
.top{max-width:1320px;margin:0 auto;padding:var(--hdpad);display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.logo{width:34px;height:34px;border-radius:var(--r);background:var(--lgbg);color:var(--lgtx);display:grid;place-items:center}
.logo .ic{width:20px;height:20px}
.brand{flex:1;min-width:180px}.brand h1{margin:0;font-size:var(--h1s);font-weight:var(--h1w);letter-spacing:var(--h1ls)}.sub{color:var(--hdmut);font-size:12.5px}
.estado{display:flex;align-items:center;gap:8px;padding:7px 14px;border-radius:var(--rp);font-weight:600;font-size:14px}
.estado .ic{width:1.25em;height:1.25em}
.estado.ok{background:var(--okb);color:var(--ok)}.estado.aviso{background:var(--avb);color:var(--av)}.estado.critico{background:var(--crb);color:var(--cr)}
.msgs{max-width:1320px;margin:0 auto;padding:0 20px 14px;list-style:none;display:grid;gap:6px}.msgs:empty{display:none}
.msgs li{display:flex;gap:8px;align-items:center;padding:8px 12px;border-radius:var(--r);font-weight:500;font-size:13.5px;background:var(--msgbg);color:var(--hdtx);border-left:3px solid}
.msgs li .ic{width:1.2em;height:1.2em}
.msgs .critico{border-color:var(--cr)}.msgs .critico .ic{color:var(--cr)}.msgs .aviso{border-color:var(--av)}.msgs .aviso .ic{color:var(--av)}.msgs .ok{border-color:var(--ok)}.msgs .ok .ic{color:var(--ok)}
main{max-width:1320px;margin:0 auto;padding:20px 20px 40px;display:grid;gap:var(--gap);grid-template-columns:minmax(0,1fr);align-items:start}
@media (min-width:1000px){main{grid-template-columns:minmax(0,1.1fr) minmax(0,1fr)}main>section:nth-of-type(3),main>footer{grid-column:1/-1}}
.card{background:var(--card);border:var(--cbd);border-radius:var(--rc);padding:var(--cpad);box-shadow:var(--sh);min-height:100%}
.card>h2,.card summary h2{margin:0 0 14px;font:var(--h2w) var(--h2s)/1.3 var(--h2f);text-transform:var(--h2t);letter-spacing:var(--h2ls);color:var(--h2c);display:flex;align-items:center;gap:8px}
.card>h2 .ic,.card summary h2 .ic{color:var(--h2ic)}
.kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--kgap);background:var(--kbg);border:var(--kbd);border-radius:var(--rk);overflow:hidden}
.kpi{background:var(--sub);padding:12px 14px}.kpi b{display:block;font-size:var(--klbs);color:var(--mut);font-weight:var(--klbw);text-transform:var(--klbt);letter-spacing:var(--klbls)}
.kpi span{font-size:var(--kvs);font-weight:var(--kvw);letter-spacing:var(--kvls);line-height:1.25;display:flex;align-items:center;gap:6px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kpi span .ic{width:.8em;height:.8em}
.kpi .error{color:var(--cr)}.kpi .aviso{color:var(--av)}.kpi .okc{color:var(--ok)}
.ctl{margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
button{font:inherit;font-size:13.5px;font-weight:var(--bw);display:inline-flex;align-items:center;gap:7px;padding:var(--bpad);border-radius:var(--rb);border:1px solid var(--bbd);background:var(--bbg);color:var(--btx);cursor:pointer;transition:background .12s,border-color .12s,filter .12s}
button:hover:not(:disabled){background:var(--bbgh)}button:disabled{opacity:.5;cursor:wait}
button.pri{background:var(--pri);border-color:var(--pri);color:var(--pritx)}button.pri:hover:not(:disabled){filter:brightness(1.08);background:var(--pri)}
button.pel{background:var(--pelbg);color:var(--peltx);border-color:var(--pelbd)}button.pel:hover:not(:disabled){background:var(--pelbg);filter:brightness(1.1)}
:focus-visible{outline:2px solid var(--ac);outline-offset:2px}
.res{display:grid;grid-template-columns:1fr;gap:18px}
.res h3{margin:0 0 8px;font-size:14px;font-weight:600;display:flex;justify-content:space-between}.res h3 small{color:var(--mut);font-weight:400}
.bar{display:flex;height:var(--barh);border-radius:var(--rbar);overflow:hidden;background:var(--bd2);margin-bottom:10px;gap:2px}.bar i{display:block;min-width:3px}
.bar .confirmada{background:var(--ok)}.bar .marcada{background:var(--ok);opacity:.6}.bar .pendiente{background:var(--pebar)}.bar .no_confirmada,.bar .vencida{background:var(--cr)}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.b{display:inline-flex;align-items:center;gap:5px;padding:var(--tagpad);border-radius:var(--rt);font-size:12px;font-weight:var(--tagw);white-space:nowrap;text-transform:var(--tagt);letter-spacing:var(--tagls)}
.confirmada,.marcada{background:var(--okb);color:var(--ok)}.pendiente{background:var(--peb);color:var(--pe)}
.vencida,.no_confirmada{background:var(--crb);color:var(--cr)}.na{color:var(--mut)}.small{font-size:12px;color:var(--mut)}
td .small{font-family:var(--fsm)}
.wrap{overflow-x:auto;margin:0 calc(var(--cpad) * -1);padding:0}table{width:100%;border-collapse:collapse}
th{font-size:var(--ths);text-transform:var(--tht);letter-spacing:var(--thls);color:var(--thc);background:var(--thbg);font-weight:600;text-align:left;padding:var(--thpad);border-bottom:1px solid var(--bd)}
th:first-child,td:first-child{padding-left:var(--cpad)}th:last-child,td:last-child{padding-right:var(--cpad)}
td{padding:var(--tdpad);border-bottom:1px solid var(--bd2);vertical-align:top}tr:last-child td{border-bottom:0}tbody tr:hover{background:var(--rowh)}
td:first-child b{font-weight:600}
.f-crit td:first-child{box-shadow:inset 3px 0 0 var(--cr)}.dup{color:var(--av);font-weight:700}
.error{color:var(--cr)}.aviso{color:var(--av)}.okc{color:var(--ok)}
ul.act{list-style:none;margin:0;padding:0;max-height:360px;overflow:auto}
ul.act li{padding:7px 0;border-bottom:1px solid var(--bd2);display:flex;gap:10px;font-size:13px}
ul.act .h{color:var(--mut);min-width:64px;font-family:var(--fsm)}ul.act .n{min-width:150px;font-weight:600}
[hidden]{display:none!important}
details summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;flex-wrap:wrap}details summary::-webkit-details-marker{display:none}
details summary h2{margin:0!important}details[open] summary{margin-bottom:12px}
.lb{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 8px}
select{font:inherit;font-size:13px;padding:5px 8px;border-radius:var(--rb);border:1px solid var(--bbd);background:var(--bbg);color:var(--tx)}
pre.log{margin:0;max-height:380px;overflow:auto;font:12px/1.55 var(--fmono);white-space:pre-wrap;word-break:break-word;background:var(--logbg);color:var(--logtx);border:1px solid var(--bd);border-radius:var(--r);padding:10px 12px}
pre.log .e{color:var(--cr);font-weight:600}pre.log .w{color:var(--av)}
footer{display:flex;gap:14px;align-items:center;flex-wrap:wrap;color:var(--mut);font-size:12px}
.pulso{width:8px;height:8px;border-radius:50%;background:var(--ok);display:inline-block;animation:p 2s infinite}
@keyframes p{50%{opacity:.25}}@media (prefers-reduced-motion:reduce){.pulso{animation:none}}
/* Novedades (vacaciones, desactivar, retiro): etiqueta bajo el nombre y diálogo Carbon (modal recto, sin sombra) */
.nov{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:4px;font-size:12px}
.nov .b{background:var(--avb);color:var(--av)}.nov .b.rem{background:var(--peb);color:var(--pe)}
button.mini{padding:2px 8px;font-size:12px;background:transparent;color:var(--ac);border-color:transparent}
button.mini:hover:not(:disabled){background:var(--rowh)}
dialog{border:0;border-radius:0;padding:0;width:min(520px,calc(100vw - 32px));background:var(--card);color:var(--tx)}
dialog::backdrop{background:rgba(22,22,22,.5)}
dialog form{padding:20px;display:grid;gap:14px}
dialog h3{margin:0;font-weight:400;font-size:20px}
dialog fieldset{border:0;margin:0;padding:0;display:grid;gap:8px}
dialog legend{font-size:12px;color:var(--mut);margin-bottom:6px;letter-spacing:.32px}
dialog label{display:flex;gap:8px;align-items:center}
.campos{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.campos label{flex-direction:column;align-items:stretch;gap:4px;font-size:12px;color:var(--mut)}
dialog input[type=date],dialog input[type=text]{font:inherit;font-size:14px;padding:9px 12px;border:0;border-bottom:1px solid var(--mut);background:var(--sub);color:var(--tx);border-radius:0;width:100%}
.pie{display:flex;gap:1px;justify-content:flex-end;margin:0 -20px -20px}
.pie button{flex:1;justify-content:flex-start;padding:14px 16px 26px}
#nov-msg{min-height:1.2em}
@media (max-width:640px){.top{padding:12px 14px}main{padding:14px}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.kpi span{font-size:20px}.ctl button{flex:1 1 auto;justify-content:center}ul.act .n{min-width:110px}}
@media (min-width:1000px) and (max-width:1250px){.kpi span{font-size:22px}}
</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="i-pin" viewBox="0 0 24 24"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></symbol>
<symbol id="i-ok" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m8 12.5 3 3 5-6"/></symbol>
<symbol id="i-warn" viewBox="0 0 24 24"><path d="M12 3.5 2.5 20h19z"/><path d="M12 10v4.5M12 17.6v.1"/></symbol>
<symbol id="i-bad" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></symbol>
<symbol id="i-check" viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5"/></symbol>
<symbol id="i-check2" viewBox="0 0 24 24"><path d="m2.5 12.5 4.5 4.5L16 8M11 16.5l.5.5L21 7.5"/></symbol>
<symbol id="i-x" viewBox="0 0 24 24"><path d="m6 6 12 12M18 6 6 18"/></symbol>
<symbol id="i-refresh" viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.6-5.9M20 4v5h-5"/></symbol>
<symbol id="i-stop" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></symbol>
<symbol id="i-play" viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z"/></symbol>
<symbol id="i-hand" viewBox="0 0 24 24"><path d="M8 12V6.5a1.5 1.5 0 0 1 3 0V11m0-1V5a1.5 1.5 0 0 1 3 0v6m0-4a1.5 1.5 0 0 1 3 0v6.5a7 7 0 0 1-7 7c-2.5 0-4-1.2-5.5-3.5L4 14.5a1.5 1.5 0 0 1 2.4-1.7L8 14.5"/></symbol>
<symbol id="i-bell" viewBox="0 0 24 24"><path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15zM10 21h4"/></symbol>
<symbol id="i-bell-off" viewBox="0 0 24 24"><path d="M6 16.5V11a6 6 0 0 1 9.5-4.9M18 11v5.5l1.5 2h-15M10 21h4M3 3l18 18"/></symbol>
<symbol id="i-pulse" viewBox="0 0 24 24"><path d="M3 12h4l2.5-6 4 12 2.5-6H21"/></symbol>
<symbol id="i-log" viewBox="0 0 24 24"><rect x="4" y="3.5" width="16" height="17" rx="2"/><path d="M8 8.5h8M8 12.5h8M8 16.5h5"/></symbol>
<symbol id="i-users" viewBox="0 0 24 24"><circle cx="9" cy="8.5" r="3.5"/><path d="M2.5 20c.5-3.6 3-5.5 6.5-5.5s6 1.9 6.5 5.5M16 5.2a3.5 3.5 0 0 1 0 6.6M18.5 14.8c1.7.7 2.7 2.3 3 5.2"/></symbol>
<symbol id="i-list" viewBox="0 0 24 24"><path d="M9 6h11M9 12h11M9 18h11M4.5 6h.1M4.5 12h.1M4.5 18h.1"/></symbol>
</defs></svg>
<header>
 <div class="top">
  <div class="logo"><svg class="ic"><use href="#i-pin"/></svg></div>
  <div class="brand"><h1>GeoVic · Monitor</h1><div class="sub" id="sub">Conectando…</div></div>
  <div class="estado ok" id="cab" role="status"><span id="cab-ic"></span><span id="titulo">Cargando…</span></div>
 </div>
 <ul class="msgs" id="msgs"></ul>
</header>
<main>
 <section class="card"><h2><svg class="ic"><use href="#i-pulse"/></svg>Programador</h2><div class="kpis" id="prog"></div>
  <div class="ctl" id="ctl" hidden>
   <button id="b-reiniciar"><svg class="ic"><use href="#i-refresh"/></svg>Reiniciar</button>
   <button id="b-detener" class="pel"><svg class="ic"><use href="#i-stop"/></svg>Detener</button>
   <button id="b-iniciar"><svg class="ic"><use href="#i-play"/></svg>Iniciar</button>
   <button id="b-marcar" class="pri" hidden><svg class="ic"><use href="#i-hand"/></svg><span id="t-marcar">Marcar pendientes</span></button>
   <span class="small" id="ctlmsg" role="status"></span></div></section>
 <section class="card"><h2><svg class="ic"><use href="#i-list"/></svg>Resumen del día</h2><div class="res" id="resumen"></div><div class="small" id="alertas" style="margin-top:10px"></div></section>
 <section class="card"><h2><svg class="ic"><use href="#i-users"/></svg>Empleados</h2><div class="wrap"><table><thead><tr><th>Empleado</th><th>Entrada</th><th>Salida</th><th>Último login</th></tr></thead><tbody id="filas"></tbody></table></div></section>
 <section class="card"><h2><svg class="ic"><use href="#i-clock"/></svg>Actividad reciente</h2><ul class="act" id="act"></ul></section>
 <section class="card"><details id="logbox"><summary><h2><svg class="ic"><use href="#i-log"/></svg>Log en vivo</h2><span class="small">usuarios y claves ocultos</span></summary>
  <div class="lb small"><select id="logsel" aria-label="Archivo de log"><option value="programador">programador</option><option value="geovictoria">geovictoria (navegador)</option></select>
   <label><input type="checkbox" id="logsolo"> solo avisos y errores</label> <span id="logarch"></span></div>
  <pre id="logtxt" class="log">Abre este panel para ver el log.</pre></details></section>
 <footer><span class="pulso" aria-hidden="true"></span><span>Se actualiza cada 5 s · <span id="ult"></span></span>
  <span>Solo lectura (salvo los botones y las novedades, solo desde este equipo)</span>
  <button id="snd"><svg class="ic"><use href="#i-bell-off"/></svg><span>Sonido apagado</span></button></footer>
</main>
<dialog id="nov" aria-labelledby="nov-tit"><form method="dialog" id="nov-form">
 <h3 id="nov-tit">Novedad</h3>
 <fieldset><legend>TIPO</legend>
  <label><input type="radio" name="tipo" value="ausencia" checked> Vacaciones, licencia o incapacidad (con fechas)</label>
  <label><input type="radio" name="tipo" value="desactivado"> Desactivar desde hoy (hasta que lo reactives)</label>
  <label><input type="radio" name="tipo" value="retiro"> Retiro (deja de marcar después de su último día)</label>
 </fieldset>
 <div class="campos" id="c-ausencia">
  <label>Desde<input type="date" id="n-desde" required></label>
  <label>Hasta (vacío = sin fecha de fin)<input type="date" id="n-hasta"></label>
  <label style="grid-column:1/-1">Motivo<input type="text" id="n-motivo" maxlength="60" list="motivos" placeholder="vacaciones"></label>
 </div>
 <div class="campos" id="c-retiro" hidden><label>Último día que marca<input type="date" id="n-ultimo"></label></div>
 <datalist id="motivos"><option value="vacaciones"><option value="licencia"><option value="incapacidad"><option value="permiso"><option value="calamidad"></datalist>
 <div class="small">Se aplica sin reiniciar el programador. Solo se guarda en config/novedades.json (sin contraseñas).</div>
 <div class="small error" id="nov-msg" role="alert"></div>
 <div class="pie"><button type="button" id="nov-cancelar">Cancelar</button><button type="submit" class="pri" id="nov-guardar">Guardar</button></div>
</form></dialog>
<script>
const Q = new URLSearchParams(location.search), T = Q.get("t");
const URL_API = "/api/estado" + (T ? "?t=" + encodeURIComponent(T) : "");
const NS = "http://www.w3.org/2000/svg";
const ico = n => { const s = document.createElementNS(NS, "svg"); s.setAttribute("class", "ic"); const u = document.createElementNS(NS, "use"); u.setAttribute("href", "#i-" + n); s.append(u); return s; };
const E = {pendiente:{t:"Pendiente",i:"clock"}, marcada:{t:"Marcada",i:"check"}, confirmada:{t:"Confirmada",i:"check2"}, no_confirmada:{t:"NO confirmada",i:"warn"}, vencida:{t:"VENCIDA",i:"bad"}};
const NIV = {ok:{t:"Todo en orden",i:"ok",c:"#1a7f45"}, aviso:{t:"Atención",i:"warn",c:"#d98b00"}, critico:{t:"CRÍTICO",i:"bad",c:"#d92d20"}};
let sonido = false, ultimoNivel = "ok", ctx = null;
const el = (t, c, x) => { const n = document.createElement(t); if (c) n.className = c; if (x !== undefined) n.textContent = x; return n; };
const con = (n, ...h) => { n.append(...h); return n; };
function pitar(){ try{ ctx = ctx || new (window.AudioContext||window.webkitAudioContext)(); const o=ctx.createOscillator(), g=ctx.createGain(); o.connect(g); g.connect(ctx.destination); o.frequency.value=880; g.gain.value=.15; o.start(); o.stop(ctx.currentTime+.4);}catch(e){} }
document.getElementById("snd").onclick = () => { sonido = !sonido; const b = document.getElementById("snd"); b.replaceChildren(ico(sonido ? "bell" : "bell-off"), el("span","", sonido ? "Sonido encendido" : "Sonido apagado")); if (sonido) pitar(); };
function insignia(estado){ const e = E[estado] || {t:estado, i:null}; return con(el("span","b "+estado), ...(e.i ? [ico(e.i)] : []), e.t); }
function favicon(c){ document.getElementById("fav").href = "data:image/svg+xml," + encodeURIComponent("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><circle cx='8' cy='8' r='7' fill='" + c + "'/></svg>"); }
function celda(a){
  const td = el("td");
  if (!a) { td.append(el("span","na","—")); return td; }
  td.append(insignia(a.estado));
  if (a.duplicada) td.append(" ", el("span","dup","×"+a.exitos+" duplicada"));
  const l = el("div","small"); let t = "programada " + (a.programada || "?");
  if (a.hora) t += " · marcó " + a.hora + (a.origen === "portal" ? " (detectada en el portal)" : "");
  if (a.detalle) t += " · " + a.detalle;
  l.textContent = t; td.append(l); return td;
}
function pintar(d){
  const cab = document.getElementById("cab"), tit = document.getElementById("titulo");
  if (d.error){ tit.textContent = "Error: " + d.error; return; }
  const nv = NIV[d.nivel] || NIV.ok; cab.className = "estado " + d.nivel;
  document.getElementById("cab-ic").replaceChildren(ico(nv.i)); tit.textContent = nv.t;
  document.getElementById("sub").textContent = new Date(d.ahora).toLocaleString("es-CO", {dateStyle:"full", timeStyle:"short"});
  const ms = document.getElementById("msgs"); ms.replaceChildren();
  d.mensajes.forEach(m => ms.append(con(el("li", m.nivel), ico(m.nivel === "critico" ? "bad" : m.nivel === "aviso" ? "warn" : "ok"), m.texto)));
  document.title = (d.nivel === "ok" ? "" : "[" + nv.t + "] ") + "GeoVic · Monitor"; favicon(nv.c);
  if (d.nivel === "critico" && ultimoNivel !== "critico" && sonido) pitar();
  ultimoNivel = d.nivel;

  const p = d.programador, g = document.getElementById("prog"); g.replaceChildren();
  const kv = (k, v, c, i) => { const x = el("div","kpi"); x.append(el("b","",k), con(el("span", c || ""), ...(i ? [ico(i)] : []), v)); g.append(x); };
  kv("Estado", p.vivo ? "Vivo" : "Sin latido", p.vivo ? "okc" : "error", p.vivo ? "ok" : "bad");
  kv("Último latido", p.edad_seg === null ? "—" : "hace " + p.edad_seg + " s");
  kv("Scheduler", p.scheduler_ok === true ? "Responde" : p.scheduler_ok === false ? "NO responde" : (p.fase || "—"), p.scheduler_ok === false ? "error" : p.scheduler_ok ? "okc" : "", p.scheduler_ok === true ? "check" : p.scheduler_ok === false ? "bad" : "");
  kv("Instancias", p.instancias === null ? "?" : String(p.instancias), p.instancias > 1 ? "aviso" : "", p.instancias > 1 ? "warn" : "");
  kv("PID", p.pid || "—"); kv("Arranques hoy", String(p.arranques_hoy));

  const r = document.getElementById("resumen"); r.replaceChildren();
  ["entrada","salida"].forEach(k => {
    const bloque = el("div"), cuentas = Object.entries(d.resumen[k]).filter(([,n]) => n > 0);
    bloque.append(con(el("h3"), (k === "entrada" ? "Entradas" : "Salidas") + " ", el("small","","(" + d.resumen.empleados + " empleados)")));
    const barra = el("div","bar"); cuentas.forEach(([e,n]) => { const s = el("i", e); s.style.flex = n; s.title = (E[e]||{t:e}).t + ": " + n; barra.append(s); });
    const chips = el("div","chips"); cuentas.forEach(([e,n]) => chips.append(con(insignia(e), " " + n)));
    bloque.append(barra, chips); r.append(bloque);
  });
  document.getElementById("alertas").textContent = "Alertas hoy: " + d.alertas.total + (d.alertas.total ? " · " + Object.entries(d.alertas.por_usuario).map(([n,c]) => n + " " + c).join(", ") : "");

  const rank = f => f.entrada && (f.entrada.estado === "vencida" || f.entrada.estado === "no_confirmada") ? 0 : 1;
  const filas = [...d.empleados].sort((a,b) => rank(a) - rank(b) || String(a.entrada&&a.entrada.programada).localeCompare(String(b.entrada&&b.entrada.programada)));
  const tb = document.getElementById("filas"); tb.replaceChildren();
  filas.forEach(f => {
    const tr = el("tr", f.entrada && (f.entrada.estado==="vencida"||f.entrada.estado==="no_confirmada") ? "f-crit" : "");
    const t1 = el("td"); t1.append(el("b","",f.nombre)); t1.append(el("div","small", f.dia === "desactivado" ? "desactivado (employees.json)" : f.dia));
    const hoy = String(d.ahora).slice(0,10);
    if (f.reemplazo) t1.append(con(el("div","nov"), el("span","b rem", f.reemplazo)));
    (f.novedades || []).forEach(n => {
      const fila = con(el("div","nov"), el("span","b", textoNov(n)));
      if (puedeEditar) { const b = el("button","mini", n.desde < hoy ? "Reactivar" : "Quitar"); b.type = "button"; b.onclick = () => terminarNov(f, n, hoy); fila.append(b); }
      t1.append(fila);
    });
    if (puedeEditar && f.dia !== "desactivado") { const b = el("button","mini","+ Novedad"); b.type = "button"; b.onclick = () => abrirNov(f); t1.append(con(el("div","nov"), b)); }
    tr.append(t1, celda(f.entrada), celda(f.salida));
    const tl = el("td");
    if (f.login) { tl.append(con(el("span", f.login.ok ? "okc" : "error"), ico(f.login.ok ? "check" : "x"), " " + f.login.hora + (f.login.ok ? "" : " " + (f.login.motivo || ""))));
      if (f.fallos_login) tl.append(el("div","small", f.fallos_login + " fallo(s) hoy")); } else tl.append(el("span","na","sin eventos"));
    tr.append(tl); tb.append(tr);
  });

  const a = document.getElementById("act"); a.replaceChildren();
  d.actividad.forEach(x => { const li = el("li", x.nivel); li.append(el("span","h",x.hora), el("span","n",x.nombre), el("span","",x.texto)); a.append(li); });
  document.getElementById("ult").textContent = "última lectura " + new Date().toLocaleTimeString("es-CO");
}
async function ciclo(){
  try { const r = await fetch(URL_API, {cache:"no-store"}); if (r.status === 401) { document.getElementById("titulo").textContent = "Falta el token en la URL (?t=…)"; return; } pintar(await r.json()); }
  catch(e){ document.getElementById("titulo").textContent = "Sin conexión con el monitor"; document.getElementById("cab").className = "estado critico"; document.getElementById("cab-ic").replaceChildren(ico("bad")); }
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
    } else msg.textContent = (d.ok ? "Listo: " : "Error: ") + d.mensaje;
  } catch(e){ msg.textContent = "Error: no se pudo contactar con el monitor."; }
  botones.forEach(b => b.disabled = false); ciclo();
}
for (const n of ["reiniciar","detener","iniciar"]) document.getElementById("b-"+n).onclick = () => { if (confirm("¿Seguro que quieres " + TXT[n] + " el programador?")) accion(n, false); };
let pendientes = [];
document.getElementById("b-marcar").onclick = () => {
  const lista = pendientes.map(p => "• " + p.nombre + " — " + p.accion).join("\n");
  if (confirm("Se intentará marcar:\n\n" + lista + "\n\nSolo se hace clic si el portal ofrece ese botón (si ya está marcado, no se duplica).\n¿Continuar?")) accion("marcar_pendientes", false);
};
// --- Novedades: vacaciones, desactivar, retiro (solo desde este equipo, igual que los botones) ---
let puedeEditar = false, empNov = null;
const fecha = s => s ? s.slice(8,10) + "/" + s.slice(5,7) + "/" + s.slice(0,4) : "";
function textoNov(n){
  if (n.tipo === "retiro") return "retiro: no marca desde " + fecha(n.desde);
  if (n.tipo === "desactivado") return "desactivado desde " + fecha(n.desde);
  return n.motivo + " " + fecha(n.desde) + (n.hasta ? " → " + fecha(n.hasta) : " → sin fecha de fin");
}
async function enviarNov(cuerpo, forzar){
  const r = await fetch("/api/accion" + (T ? "?t=" + encodeURIComponent(T) : ""), {method:"POST",
    headers:{"Content-Type":"application/json","X-GeoVic-Accion":"1"}, body: JSON.stringify({accion:"novedad", forzar:!!forzar, ...cuerpo})});
  const d = await r.json();
  if (r.status === 409 && d.bloqueado && !forzar) {
    if (confirm(d.mensaje + "\n\n¿Guardar de todos modos?")) return enviarNov(cuerpo, true);
    return {ok:false, mensaje:"No se guardó nada."};
  }
  return d;
}
function mostrarCampos(){
  const t = document.querySelector("#nov-form input[name=tipo]:checked").value;
  document.getElementById("c-ausencia").hidden = t !== "ausencia";
  document.getElementById("c-retiro").hidden = t !== "retiro";
  document.getElementById("n-desde").required = t === "ausencia";
  document.getElementById("n-ultimo").required = t === "retiro";
}
document.querySelectorAll("#nov-form input[name=tipo]").forEach(r => r.onchange = mostrarCampos);
function abrirNov(f){
  empNov = f;
  const form = document.getElementById("nov-form"); form.reset();
  document.getElementById("nov-tit").textContent = "Novedad · " + f.nombre;
  document.getElementById("nov-msg").textContent = "";
  const hoy = new Date(); hoy.setMinutes(hoy.getMinutes() - hoy.getTimezoneOffset());
  document.getElementById("n-desde").value = hoy.toISOString().slice(0,10);
  mostrarCampos(); document.getElementById("nov").showModal();
}
document.getElementById("nov-cancelar").onclick = () => document.getElementById("nov").close();
document.getElementById("nov-form").onsubmit = async ev => {
  ev.preventDefault();
  const tipo = document.querySelector("#nov-form input[name=tipo]:checked").value, msg = document.getElementById("nov-msg");
  const cuerpo = {op:"agregar", emp_id:empNov.id, tipo, desde:document.getElementById("n-desde").value,
                  hasta:document.getElementById("n-hasta").value || null, motivo:document.getElementById("n-motivo").value,
                  ultimo_dia:document.getElementById("n-ultimo").value};
  if (tipo === "desactivado" && !confirm(empNov.nombre + " dejará de marcar desde HOY hasta que lo reactives. ¿Continuar?")) return;
  const g = document.getElementById("nov-guardar"); g.disabled = true; msg.textContent = "Guardando…";
  try {
    const d = await enviarNov(cuerpo, false);
    if (d.ok) { document.getElementById("nov").close(); document.getElementById("ctlmsg").textContent = d.mensaje; ciclo(); }
    else msg.textContent = d.mensaje;
  } catch(e){ msg.textContent = "No se pudo contactar con el monitor."; }
  g.disabled = false;
};
async function terminarNov(f, n, hoy){
  const enCurso = n.desde <= hoy;
  const txt = enCurso ? f.nombre + " vuelve a marcar desde HOY (" + textoNov(n) + ").\n\nSi ya pasó su hora de entrada, el programador la marcará en su próxima revisión horaria (hasta las 12:00)."
                      : "Quitar la novedad de " + f.nombre + ": " + textoNov(n) + ".";
  if (!confirm(txt + "\n\n¿Continuar?")) return;
  try { const d = await enviarNov({op:"terminar", id:n.id}, true); document.getElementById("ctlmsg").textContent = (d.ok ? "" : "Error: ") + d.mensaje; }
  catch(e){ document.getElementById("ctlmsg").textContent = "Error: no se pudo contactar con el monitor."; }
  ciclo();
}
async function cicloControl(){
  try {
    const r = await fetch("/api/control" + (T ? "?t=" + encodeURIComponent(T) : ""), {cache:"no-store"}); const d = await r.json();
    if (puedeEditar !== !!d.permitido) { puedeEditar = !!d.permitido; ciclo(); }
    document.getElementById("ctl").hidden = !d.permitido;
    pendientes = d.pendientes || [];
    const bm = document.getElementById("b-marcar"); bm.hidden = !pendientes.length;
    document.getElementById("t-marcar").textContent = "Marcar pendientes (" + pendientes.length + ")";
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
    print(f"✅ Monitor en {url}   (Ctrl+C para cerrar)")
    if args.abrir:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nMonitor cerrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
