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


def test_es_de_solo_lectura(monitor_mod, empleados_json):
    srv = _servidor(monitor_mod, empleados_json)
    try:
        for metodo in ("POST", "PUT", "DELETE"):
            c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
            c.request(metodo, "/api/estado", body="x")
            r = c.getresponse()
            r.read()
            assert r.status in (405, 501)  # sin do_POST/do_PUT/do_DELETE: no hay forma de modificar nada
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
