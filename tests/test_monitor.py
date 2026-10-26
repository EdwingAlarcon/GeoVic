"""Tests de scripts/monitor.py: servidor de solo lectura, token y que nunca filtre credenciales."""
import http.client
import importlib.util
import json
import threading
from datetime import datetime
from pathlib import Path

import pytest

from src import bitacora

RUTA = Path(__file__).parent.parent / "scripts" / "monitor.py"
SECRETO = "S3cr3t0-Unico"


@pytest.fixture(scope="module")
def monitor_mod():
    spec = importlib.util.spec_from_file_location("monitor_script", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def empleados_json(tmp_path, monkeypatch):
    monkeypatch.setattr(bitacora, "LOG_DIR", tmp_path)
    ruta = tmp_path / "employees.json"
    ruta.write_text(json.dumps({"employees": [
        {"id": "e1", "nombre": "Ana", "usuario": "ana@correo.test", "password": SECRETO, "activo": True},
        {"id": "e2", "nombre": "Luis", "usuario": "luis@correo.test", "password": SECRETO, "activo": False},
    ]}), encoding="utf-8")
    return ruta


def _servidor(monitor_mod, ruta, token=None):
    srv = monitor_mod.Monitor(("127.0.0.1", 0), token, ruta)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _get(srv, camino, cabeceras=None):
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    c.request("GET", camino, headers=cabeceras or {})
    r = c.getresponse()
    return r.status, r.read().decode("utf-8")


def test_sirve_la_pagina_y_el_estado(monitor_mod, empleados_json):
    srv = _servidor(monitor_mod, empleados_json)
    try:
        estado, html = _get(srv, "/")
        assert estado == 200 and "GeoVic" in html and "/api/estado" in html

        estado, cuerpo = _get(srv, "/api/estado")
        datos = json.loads(cuerpo)
        assert estado == 200 and [e["nombre"] for e in datos["empleados"]] == ["Ana", "Luis"]
        assert datos["empleados"][1]["dia"] == "desactivado"
    finally:
        srv.shutdown()


def test_nunca_sirve_usuarios_ni_contrasenas(monitor_mod, empleados_json):
    srv = _servidor(monitor_mod, empleados_json)
    try:
        _, cuerpo = _get(srv, "/api/estado")
        _, html = _get(srv, "/")
        for texto in (cuerpo, html):
            assert SECRETO not in texto and "ana@correo.test" not in texto and "luis@correo.test" not in texto
    finally:
        srv.shutdown()


def test_con_token_rechaza_sin_el_y_acepta_con_el(monitor_mod, empleados_json):
    srv = _servidor(monitor_mod, empleados_json, token="clave-larga")
    try:
        assert _get(srv, "/")[0] == 401
        assert _get(srv, "/api/estado")[0] == 401
        assert _get(srv, "/api/estado?t=equivocado")[0] == 401
        assert _get(srv, "/api/estado?t=clave-larga")[0] == 200
        assert _get(srv, "/api/estado", {"X-Token": "clave-larga"})[0] == 200
        assert _get(srv, "/?t=clave-larga")[0] == 200
    finally:
        srv.shutdown()


def test_solo_hay_una_ruta_que_actua(monitor_mod, empleados_json):
    """Todo es lectura salvo POST /api/accion (protegida): cualquier otro método o ruta no modifica nada."""
    srv = _servidor(monitor_mod, empleados_json)
    try:
        for metodo in ("PUT", "DELETE", "PATCH"):
            c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
            c.request(metodo, "/api/estado", body="x")
            r = c.getresponse()
            r.read()
            assert r.status in (405, 501)  # sin do_PUT/do_DELETE/do_PATCH
        c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
        c.request("POST", "/api/estado", body="x")
        r = c.getresponse()
        r.read()
        assert r.status == 404  # POST solo existe en /api/accion
        assert _get(srv, "/otra-cosa")[0] == 404
    finally:
        srv.shutdown()


def test_sin_lista_de_empleados_devuelve_error_en_vez_de_romper(monitor_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(bitacora, "LOG_DIR", tmp_path)
    monkeypatch.setattr(monitor_mod.dl, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("GEOVICTORIA_USER", raising=False)
    monkeypatch.delenv("GEOVICTORIA_PASSWORD", raising=False)
    datos = monitor_mod.leer_estado(tmp_path / "no_existe.json")
    assert "error" in datos


def test_un_registro_a_medio_escribir_no_se_confunde_con_sin_marcaje(monitor_mod, empleados_json, tmp_path):
    hoy = datetime.now().strftime("%Y-%m-%d")
    valido = {hoy: {"ENTRADA SEMANA (L-V)": {"ejecutado": True, "hora": f"{hoy}T07:00:30", "origen": "programador"}}}
    ruta = tmp_path / "registro_e1.json"
    ruta.write_text(json.dumps(valido), encoding="utf-8")
    emps = [{"id": "e1"}]
    assert monitor_mod._leer_registros(emps)["e1"] == valido

    ruta.write_text('{"2026-10-26": {"ENTRADA SEMANA (L-V)": {"ejec', encoding="utf-8")  # el programador está escribiendo
    assert monitor_mod._leer_registros(emps)["e1"] == valido  # conserva la última lectura buena, no {}

    ruta.unlink()  # sin archivo = realmente no hay registro
    assert monitor_mod._leer_registros(emps)["e1"] == {}


def test_los_registros_y_alertas_de_hoy_se_leen(monitor_mod, empleados_json, tmp_path):
    hoy = datetime.now().strftime("%Y-%m-%d")
    (tmp_path / "registro_e1.json").write_text(json.dumps({hoy: {"ENTRADA SEMANA (L-V)": {
        "ejecutado": True, "hora": f"{hoy}T07:00:30", "origen": "portal"}}}), encoding="utf-8")
    (tmp_path / "alertas.log").write_text(f"{hoy}T08:00:00.1 | ALERTA | Ana | ENTRADA SEMANA (L-V) no ejecutado\n"
                                          "2020-01-01T08:00:00.1 | ALERTA | Luis | vieja\n", encoding="utf-8")
    datos = monitor_mod.leer_estado(empleados_json)
    assert datos["alertas"] == {"total": 1, "por_usuario": {"Ana": 1}}
    ana = datos["empleados"][0]
    if ana["dia"] == "semana":  # la clave del registro es la de L-V; en sábado/domingo/festivo no aplica
        assert ana["entrada"]["estado"] == "confirmada" and ana["entrada"]["hora"] == "07:00:30"


def _escribir_log(tmp_path, nombre, lineas):
    (tmp_path / f"{nombre}_{datetime.now().strftime('%Y%m%d')}.log").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def test_log_oculta_usuarios_y_contrasenas(monitor_mod, empleados_json, tmp_path):
    _escribir_log(tmp_path, "geovictoria", [
        "2026-10-26 08:00:01 INFO [Ana] Usuario: ana@correo.test",
        f"2026-10-26 08:00:02 ERROR clave {SECRETO} rechazada para luis@correo.test",
        "2026-10-26 08:00:03 INFO login correcto",
    ])
    srv = _servidor(monitor_mod, empleados_json)
    try:
        estado, cuerpo = _get(srv, "/api/log?f=geovictoria")
        assert estado == 200
        for prohibido in (SECRETO, "ana@correo.test", "luis@correo.test"):
            assert prohibido not in cuerpo
        assert "login correcto" in cuerpo and "***" in cuerpo
    finally:
        srv.shutdown()


def test_log_solo_acepta_los_logs_conocidos_y_devuelve_el_final(monitor_mod, empleados_json, tmp_path):
    _escribir_log(tmp_path, "programador", [f"linea {i}" for i in range(1000)])
    srv = _servidor(monitor_mod, empleados_json)
    try:
        _, cuerpo = _get(srv, "/api/log?f=programador&n=30")
        lineas = json.loads(cuerpo)["lineas"]
        assert len(lineas) == 30 and lineas[-1] == "linea 999"

        for malo in ("../employees", "..%5Cconfig%5Cemployees", "alertas"):
            estado, cuerpo = _get(srv, f"/api/log?f={malo}")
            assert estado == 200 and json.loads(cuerpo)["lineas"] == []

        _, cuerpo = _get(srv, "/api/log?f=geovictoria")  # sin archivo hoy: vacío, sin error
        assert json.loads(cuerpo)["lineas"] == []
    finally:
        srv.shutdown()


def test_log_exige_token_si_hay_token(monitor_mod, empleados_json):
    srv = _servidor(monitor_mod, empleados_json, token="CLAVE")
    try:
        assert _get(srv, "/api/log?f=programador")[0] == 401
        assert _get(srv, "/api/log?f=programador&t=CLAVE")[0] == 200
    finally:
        srv.shutdown()


# --- Botones de control: POST /api/accion --------------------------------------

def _post(srv, cuerpo, cabeceras=None, camino="/api/accion"):
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    c.request("POST", camino, body=json.dumps(cuerpo), headers={"Content-Type": "application/json", **(cabeceras or {})})
    r = c.getresponse()
    return r.status, json.loads(r.read().decode("utf-8"))


OK = {"X-GeoVic-Accion": "1"}


@pytest.fixture
def control(monitor_mod, empleados_json, monkeypatch):
    llamadas = []
    monkeypatch.setattr(monitor_mod, "ejecutar_accion", lambda accion, raiz=None: llamadas.append(accion) or f"hecho {accion}")
    monkeypatch.setattr(monitor_mod.estado_monitor, "bloqueo_por_marcaje", lambda estado, ahora: None)
    srv = _servidor(monitor_mod, empleados_json)
    yield srv, llamadas
    srv.shutdown()


def test_accion_ejecuta_y_queda_en_la_bitacora(control):
    srv, llamadas = control
    estado, cuerpo = _post(srv, {"accion": "reiniciar"}, OK)
    assert (estado, cuerpo["ok"]) == (200, True) and llamadas == ["reiniciar"]
    assert any(e["tipo"] == "control" and e["accion"] == "reiniciar" and e["ok"] for e in bitacora.leer_eventos())


def test_accion_exige_la_cabecera_propia_y_rechaza_otro_origen(control):
    srv, llamadas = control
    assert _post(srv, {"accion": "reiniciar"})[0] == 403  # sin cabecera (p. ej. un formulario ajeno)
    assert _post(srv, {"accion": "reiniciar"}, {**OK, "Origin": "http://malo.example"})[0] == 403
    assert llamadas == []


def test_accion_valida_el_cuerpo(control):
    srv, llamadas = control
    assert _post(srv, {"accion": "borrar_todo"}, OK)[0] == 400
    assert _post(srv, {}, OK)[0] == 400
    assert _post(srv, {"accion": "reiniciar"}, OK, camino="/api/otra")[0] == 404
    assert llamadas == []


def test_accion_bloqueada_por_un_marcaje_exige_forzar(monitor_mod, empleados_json, monkeypatch):
    llamadas = []
    monkeypatch.setattr(monitor_mod, "ejecutar_accion", lambda accion, raiz=None: llamadas.append(accion) or "ok")
    monkeypatch.setattr(monitor_mod.estado_monitor, "bloqueo_por_marcaje", lambda estado, ahora: "Ana: su entrada está programada")
    srv = _servidor(monitor_mod, empleados_json)
    try:
        estado, cuerpo = _post(srv, {"accion": "reiniciar"}, OK)
        assert estado == 409 and cuerpo["bloqueado"] and llamadas == []
        assert _post(srv, {"accion": "reiniciar", "forzar": True}, OK)[0] == 200 and llamadas == ["reiniciar"]
        assert any(e["tipo"] == "control" and e["forzado"] for e in bitacora.leer_eventos())
        llamadas.clear()
        assert _post(srv, {"accion": "iniciar"}, OK)[0] == 200  # iniciar nunca se bloquea
    finally:
        srv.shutdown()


def test_accion_exige_token_y_un_fallo_se_informa(monitor_mod, empleados_json, monkeypatch):
    def falla(accion, raiz=None):
        raise RuntimeError("no arrancó")

    monkeypatch.setattr(monitor_mod, "ejecutar_accion", falla)
    monkeypatch.setattr(monitor_mod.estado_monitor, "bloqueo_por_marcaje", lambda estado, ahora: None)
    srv = _servidor(monitor_mod, empleados_json, token="CLAVE")
    try:
        assert _post(srv, {"accion": "reiniciar"}, OK)[0] == 401
        estado, cuerpo = _post(srv, {"accion": "reiniciar"}, OK, camino="/api/accion?t=CLAVE")
        assert estado == 500 and "no arrancó" in cuerpo["mensaje"]
        assert any(e["tipo"] == "control" and e["ok"] is False for e in bitacora.leer_eventos())
    finally:
        srv.shutdown()


def test_ejecutar_accion_reiniciar_detiene_inicia_y_espera(monitor_mod, monkeypatch):
    pasos = []
    cp = monitor_mod.control_programador
    monkeypatch.setattr(cp, "detener", lambda: pasos.append("detener") or 2)
    monkeypatch.setattr(cp, "procesos_programador", lambda: [])
    monkeypatch.setattr(cp, "iniciar", lambda raiz: pasos.append("iniciar") or 1)
    monkeypatch.setattr(cp, "esperar_arranque", lambda: True)
    assert "reiniciado" in monitor_mod.ejecutar_accion("reiniciar") and pasos == ["detener", "iniciar"]

    monkeypatch.setattr(cp, "esperar_arranque", lambda: False)
    with pytest.raises(RuntimeError):
        monitor_mod.ejecutar_accion("reiniciar")

    monkeypatch.setattr(cp, "procesos_programador", lambda: [object()])
    with pytest.raises(RuntimeError, match="Ya hay"):
        monitor_mod.ejecutar_accion("iniciar")


def test_control_informa_si_se_permite_y_el_bloqueo(monitor_mod, empleados_json, monkeypatch):
    monkeypatch.setattr(monitor_mod.estado_monitor, "bloqueo_por_marcaje", lambda estado, ahora: "Ana: algo")
    srv = _servidor(monitor_mod, empleados_json)
    try:
        estado, cuerpo = _get(srv, "/api/control")
        assert estado == 200 and json.loads(cuerpo) == {"permitido": True, "bloqueo": "Ana: algo"}
    finally:
        srv.shutdown()
