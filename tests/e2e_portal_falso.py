#!/usr/bin/env python3
"""
Prueba de punta a punta (≈6 min): el programador REAL y el monitor REAL contra un portal FALSO con estado.

Ejecutar a mano (pytest NO la recoge: el nombre no empieza por test_):
    python tests/e2e_portal_falso.py

Cubre lo que importa para tener certeza de que se marcó:
  u1, u2  marcan bien y deben quedar CONFIRMADOS por el segundo login.
  u3      el clic "funciona" pero el portal NO lo guarda: debe salir NO CONFIRMADO y disparar alerta.
  u4      clave mala: login fallido y marcaje VENCIDO.
  Además: latido vivo, una sola instancia, 0 clics duplicados y ninguna credencial en la bitácora.

Trabaja en una copia temporal con empleados ficticios. No toca config/employees.json ni el portal real.
Hay que lanzarla un día laborable (el programador no marca en domingo ni en festivo).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parent.parent
PORT_MONITOR = 8793

estado = {"u1": "Entrada", "u2": "Entrada", "u3": "Entrada", "u4": "Entrada"}
clics = {k: 0 for k in estado}
PERDER = {"u3"}  # su clic "funciona" pero el portal NO lo registra
LOGIN = ('<html><body>{m}<form method="post" action="/account/login"><input id="user" name="u">'
         '<input type="password" name="p"><button id="btnLogin" type="submit">Ingresar</button></form></body></html>')


class PortalFalso(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _s(self, code, body, loc=None):
        self.send_response(code)
        if loc:
            self.send_header("Location", loc)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        u = urlparse(self.path)
        usr = parse_qs(u.query).get("u", [""])[0]
        if u.path.startswith("/account/login"):
            self._s(200, LOGIN.format(m=""))
        elif u.path == "/portal/home":
            self._s(200, f'<html><body>Inicio<iframe src="/frame?u={usr}&x=gvportal.geovictoria.com"></iframe></body></html>')
        elif u.path == "/frame":
            e = estado.get(usr)
            self._s(200, f'<html><body><button data-help-title="Marcar {e}" onclick="fetch(\'/marcar?u={usr}\')'
                         f'.then(()=>this.remove())">Marcar {e}</button></body></html>' if e else "<html><body>nada</body></html>")
        elif u.path == "/marcar":
            clics[usr] += 1
            if usr not in PERDER:
                estado[usr] = "Salida" if estado[usr] == "Entrada" else "Entrada"
            self._s(200, "ok")
        else:
            self._s(404, "x")

    def do_POST(self):
        d = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
        usr, pwd = d.get("u", [""])[0], d.get("p", [""])[0]
        if pwd == "ok" and usr in estado and usr != "u4":
            self._s(302, "", f"/portal/home?u={usr}")
        else:
            self._s(200, LOGIN.format(m='<div class="text-danger">Usuario o contraseña incorrectos</div>'))


def api():
    try:
        return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT_MONITOR}/api/estado", timeout=8).read().decode())
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def main() -> int:
    if datetime.now().weekday() == 6:
        print("Hoy es domingo: el programador no marca. Ejecútala un día laborable.")
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="geovic_e2e_"))
    sandbox = tmp / "proyecto"
    servidor = HTTPServer(("127.0.0.1", 0), PortalFalso)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{servidor.server_address[1]}/account/login"
    procesos = []
    try:
        shutil.copytree(REPO / "src", sandbox / "src", ignore=shutil.ignore_patterns("logs", "__pycache__"))
        shutil.copytree(REPO / "scripts", sandbox / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        (sandbox / "config").mkdir()
        for f in ("selectors.json", "festivos_adicionales.json"):
            if (REPO / "config" / f).exists():
                shutil.copy(REPO / "config" / f, sandbox / "config" / f)

        objetivo = datetime.now() + timedelta(seconds=100)
        nombres = [("u1", "Uno"), ("u2", "Dos"), ("u3", "Tres perdida"), ("u4", "Cuatro clave mala")]
        empleados = {"employees": [
            {"id": f"t{i}", "nombre": f"Prueba {n}", "usuario": u, "password": "ok", "activo": True,
             "horario": {"entrada_semana_hora": objetivo.hour, "entrada_semana_minuto": objetivo.minute,
                         "salida_semana_hora": 23, "salida_semana_minuto": 30, "trabaja_sabados": False}}
            for i, (u, n) in enumerate(nombres, 1)]}
        ruta_emp = sandbox / "config" / "employees.json"
        ruta_emp.write_text(json.dumps(empleados), encoding="utf-8")

        env = dict(os.environ, GEOVICTORIA_LOGIN_URL=url, GEOVICTORIA_HEADLESS="1",
                   GEOVICTORIA_CONFIRMAR_DEMORA="20", PYTHONIOENCODING="utf-8")
        procesos.append(subprocess.Popen([sys.executable, "src/programador.py"], cwd=sandbox, env=env,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        procesos.append(subprocess.Popen([sys.executable, "scripts/monitor.py", "--puerto", str(PORT_MONITOR),
                                          "--empleados", str(ruta_emp)], cwd=sandbox, env=env,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        fin = objetivo + timedelta(seconds=250)
        print(f"Ahora {datetime.now():%H:%M:%S}; entrada programada {objetivo:%H:%M} (+0..30 s); termina ~{fin:%H:%M:%S}", flush=True)
        while datetime.now() < fin:
            time.sleep(30)
            d = api()
            print(f"  {datetime.now():%H:%M:%S} " + (d.get("error", "") or f"nivel={d['nivel']} " + " ".join(
                f"{e['nombre'].split()[1][:4]}:{e['entrada']['estado']}" for e in d["empleados"])), flush=True)
        d = api()

        logs = sandbox / "src" / "logs"
        eventos = [json.loads(l) for l in (sorted(logs.glob("eventos_*.jsonl"))[-1]).read_text(encoding="utf-8").splitlines()]
        alertas = (logs / "alertas.log").read_text(encoding="utf-8") if (logs / "alertas.log").exists() else ""
    finally:
        for p in procesos:
            p.kill()
        servidor.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    fila = {e["nombre"].split()[1]: e["entrada"] for e in d.get("empleados", [])}
    comprobaciones = [
        ("el monitor responde", "error" not in d),
        ("programador vivo con latido", d["programador"]["vivo"]),
        ("scheduler responde", d["programador"]["scheduler_ok"] is True),
        ("una sola instancia", d["programador"]["instancias"] == 1),
        ("u1 marcó y quedó CONFIRMADA", fila["Uno"]["estado"] == "confirmada" and fila["Uno"]["exitos"] == 1),
        ("u2 marcó y quedó CONFIRMADA", fila["Dos"]["estado"] == "confirmada" and fila["Dos"]["exitos"] == 1),
        ("u3 (clic perdido) salió NO CONFIRMADA", fila["Tres"]["estado"] == "no_confirmada"),
        ("u3 disparó la alerta del portal", "NO CONFIRMADO por el portal" in alertas),
        ("u4 (clave mala) quedó VENCIDA sin marcaje", fila["Cuatro"]["estado"] == "vencida" and fila["Cuatro"]["hora"] is None),
        ("el nivel general es CRÍTICO", d["nivel"] == "critico"),
        ("0 clics duplicados (1, 1, 1 y 0)", clics == {"u1": 1, "u2": 1, "u3": 1, "u4": 0}),
        ("la bitácora no contiene credenciales", not any(k in json.dumps(eventos) for k in ('"password"', '"usuario"'))),
    ]
    print()
    for texto, ok in comprobaciones:
        print(("  OK    " if ok else "  FALLA ") + texto)
    fallos = [t for t, ok in comprobaciones if not ok]
    print(f"\n{'TODO OK' if not fallos else str(len(fallos)) + ' FALLO(S)'} · clics en el portal: {clics}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
