"""Tests de novedades (vacaciones, desactivar, retiro) gestionadas desde el monitor.

Lo crítico: lo guardado se aplica sin reiniciar, nunca se escribe en employees.json, y un archivo
ilegible no se toma como "sin novedades" (marcaría a gente de vacaciones).
"""
import http.client
import importlib.util
import json
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from src import bitacora
from src import empleados as emps
from src import novedades as nov

HOY = date(2026, 11, 23)  # lunes
IDS = ["e1", "e2"]


def construir(**datos):
    return nov.construir({"emp_id": "e1", "tipo": "ausencia", **datos}, IDS, HOY)


# --- construir: validación ------------------------------------------------------

def test_ausencia_con_fechas_y_motivo_limpio():
    n = construir(desde="2026-12-20", hasta="2027-01-10", motivo="  vacaciones   de fin de año ")
    assert (n["desde"], n["hasta"], n["motivo"], n["tipo"]) == ("2026-12-20", "2027-01-10", "vacaciones de fin de año", "ausencia")
    assert n["id"].startswith("n") and len(n["id"]) == 9
    assert set(n) == {"id", "emp_id", "tipo", "desde", "hasta", "motivo", "creada"}  # nada de credenciales


def test_ausencia_sin_hasta_y_motivo_por_defecto():
    n = construir(desde="2026-11-23")
    assert n["hasta"] is None and n["motivo"] == "ausencia"


def test_una_incapacidad_sin_fin_que_empezo_antes_se_acepta():
    n = construir(desde="2026-11-19", motivo="incapacidad")  # empezó el jueves, se registra el lunes
    assert (n["desde"], n["hasta"]) == ("2026-11-19", None)


def test_desactivar_es_desde_hoy_y_sin_fin():
    n = nov.construir({"emp_id": "e2", "tipo": "desactivado", "desde": "2030-01-01"}, IDS, HOY)
    assert (n["desde"], n["hasta"], n["motivo"]) == ("2026-11-23", None, "desactivado")


def test_retiro_deja_de_marcar_el_dia_siguiente_al_ultimo():
    n = nov.construir({"emp_id": "e1", "tipo": "retiro", "ultimo_dia": "2026-12-15"}, IDS, HOY)
    assert (n["desde"], n["hasta"], n["motivo"]) == ("2026-12-16", None, "retiro")


def test_el_motivo_se_recorta():
    assert len(construir(desde="2026-11-23", motivo="x" * 500)["motivo"]) == nov.MOTIVO_MAX


@pytest.mark.parametrize("datos, error", [
    ({"emp_id": "otro"}, "desconocido"),
    ({"tipo": "borrar"}, "Tipo"),
    ({"desde": "23/11/2026"}, "AAAA-MM-DD"),
    ({"desde": ""}, "AAAA-MM-DD"),
    ({"desde": "2026-12-10", "hasta": "pronto"}, "AAAA-MM-DD"),
    ({"desde": "2026-12-10", "hasta": "2026-12-01"}, "anterior"),
    ({"desde": "2026-11-01", "hasta": "2026-11-20"}, "ya terminó"),
    ({"desde": "2062-11-23"}, "revisa el año"),
    ({"desde": "2026-12-01", "hasta": "2062-12-01"}, "revisa el año"),
    ({"tipo": "retiro", "ultimo_dia": ""}, "último día"),
    ({"tipo": "retiro", "ultimo_dia": "2026-11-01"}, "anterior a ayer"),
])
def test_rechaza_datos_invalidos_con_un_mensaje_claro(datos, error):
    with pytest.raises(nov.NovedadInvalida, match=error):
        nov.construir({"emp_id": "e1", "tipo": "ausencia", "desde": "2026-12-01", **datos}, IDS, HOY)


# --- leer / agregar / terminar ----------------------------------------------------

def test_sin_archivo_no_hay_novedades_ni_error(tmp_path):
    assert nov.leer(tmp_path / "novedades.json") == ([], None)


def test_agregar_y_leer(tmp_path):
    ruta = tmp_path / "novedades.json"
    n = nov.agregar(ruta, construir(desde="2026-12-01", hasta="2026-12-05", motivo="vacaciones"))
    leidas, error = nov.leer(ruta)
    assert error is None and leidas == [n]
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"novedades": [n]}


def test_no_se_admiten_dos_novedades_que_se_cruzan(tmp_path):
    ruta = tmp_path / "novedades.json"
    nov.agregar(ruta, construir(desde="2026-12-01", hasta="2026-12-10", motivo="vacaciones"))
    with pytest.raises(nov.NovedadInvalida, match="Se cruza"):
        nov.agregar(ruta, construir(desde="2026-12-10", hasta="2026-12-12"))
    with pytest.raises(nov.NovedadInvalida, match="Se cruza"):
        nov.agregar(ruta, construir(desde="2026-11-25"))  # sin fin: se cruza con todo lo posterior
    nov.agregar(ruta, construir(desde="2026-12-11", hasta="2026-12-12"))  # contigua: vale
    nov.agregar(ruta, {**construir(desde="2026-12-01"), "emp_id": "e2"})  # otra persona: vale
    assert len(nov.leer(ruta)[0]) == 3


def test_quitar_una_futura_la_elimina(tmp_path):
    ruta = tmp_path / "novedades.json"
    n = nov.agregar(ruta, construir(desde="2026-12-01", hasta="2026-12-05"))
    assert nov.terminar(ruta, n["id"], HOY) == (n, "eliminada")
    assert nov.leer(ruta)[0] == []


def test_quitar_una_que_empieza_hoy_la_elimina_en_vez_de_dejar_un_rango_invalido(tmp_path):
    ruta = tmp_path / "novedades.json"
    n = nov.agregar(ruta, nov.construir({"emp_id": "e1", "tipo": "desactivado"}, IDS, HOY))
    assert nov.terminar(ruta, n["id"], HOY)[1] == "eliminada"
    assert nov.leer(ruta)[0] == []


def test_reactivar_una_en_curso_la_cierra_ayer_y_conserva_el_historial(tmp_path):
    ruta = tmp_path / "novedades.json"
    n = nov.agregar(ruta, nov.construir({"emp_id": "e1", "tipo": "desactivado"}, IDS, HOY - timedelta(days=5)))
    _, como = nov.terminar(ruta, n["id"], HOY)
    assert como == "cerrada"
    (guardada,), _ = nov.leer(ruta)
    assert guardada["hasta"] == "2026-11-22" and guardada["desde"] == "2026-11-18"
    assert emps.ausencia_en(nov.combinar({"id": "e1"}, [guardada]), HOY) is None  # hoy vuelve a marcar
    assert emps.ausencia_en(nov.combinar({"id": "e1"}, [guardada]), HOY - timedelta(days=1)) == "desactivado"


def test_terminar_una_inexistente_avisa(tmp_path):
    with pytest.raises(nov.NovedadInvalida, match="ya no existe"):
        nov.terminar(tmp_path / "novedades.json", "nxxxx", HOY)


def test_un_archivo_ilegible_no_se_toma_como_sin_novedades(tmp_path):
    ruta = tmp_path / "novedades.json"
    n = nov.agregar(ruta, construir(desde="2026-11-23", motivo="vacaciones"))
    ruta.write_text("{ roto", encoding="utf-8")
    leidas, error = nov.leer(ruta)
    assert leidas == [n] and "ilegible" in error  # se sigue respetando la última lectura buena
    with pytest.raises(nov.NovedadInvalida, match="No se guarda nada"):
        nov.agregar(ruta, construir(desde="2026-12-20"))
    assert ruta.read_text(encoding="utf-8") == "{ roto"  # no se pisa: hay que corregirlo a mano


def test_ilegible_sin_lectura_previa_avisa(tmp_path):
    ruta = tmp_path / "novedades.json"
    ruta.write_text('{"otra": 1}', encoding="utf-8")
    leidas, error = nov.leer(ruta)
    assert leidas == [] and error


def test_vigentes_o_futuras_omite_las_terminadas():
    lista = [{"id": "a", "emp_id": "e1", "desde": "2026-11-01", "hasta": "2026-11-10", "motivo": "x"},
             {"id": "b", "emp_id": "e1", "desde": "2026-12-01", "hasta": None, "motivo": "y"},
             {"id": "c", "emp_id": "e1", "desde": "2026-11-20", "hasta": "2026-11-23", "motivo": "z"},
             {"id": "d", "emp_id": "e2", "desde": "2026-11-20", "hasta": None, "motivo": "w"}]
    assert [n["id"] for n in nov.vigentes_o_futuras(lista, "e1", HOY)] == ["c", "b"]


# --- el programador las ve sin reiniciar -------------------------------------------

def test_ausencia_vigente_suma_las_novedades_del_monitor(tmp_path, monkeypatch):
    archivo = tmp_path / "employees.json"
    archivo.write_text(json.dumps({"employees": [{"id": "e1", "nombre": "Ana"}]}), encoding="utf-8")
    monkeypatch.setattr(emps, "EMPLOYEES_FILE", archivo)
    cargado_al_arrancar = {"id": "e1", "nombre": "Ana"}
    assert emps.ausencia_vigente(cargado_al_arrancar, HOY) is None
    nov.agregar(tmp_path / "novedades.json", construir(desde="2026-11-23", hasta="2026-11-27", motivo="incapacidad"))
    assert emps.ausencia_vigente(cargado_al_arrancar, HOY) == "incapacidad"
    assert emps.ausencia_vigente(cargado_al_arrancar, date(2026, 11, 28)) is None


def test_las_ausencias_de_employees_json_siguen_valiendo(tmp_path, monkeypatch):
    archivo = tmp_path / "employees.json"
    archivo.write_text(json.dumps({"employees": [{"id": "e1", "ausencias": [{"desde": "2026-11-23", "motivo": "a mano"}]}]}),
                       encoding="utf-8")
    monkeypatch.setattr(emps, "EMPLOYEES_FILE", archivo)
    nov.agregar(tmp_path / "novedades.json", {**construir(desde="2026-11-23"), "emp_id": "e2"})
    assert emps.ausencia_vigente({"id": "e1"}, HOY) == "a mano"


# --- monitor: lectura y POST /api/accion --------------------------------------------

RUTA_MONITOR = Path(__file__).parent.parent / "scripts" / "monitor.py"
SECRETO = "S3cr3t0-Unico"
OK = {"X-GeoVic-Accion": "1"}


@pytest.fixture(scope="module")
def monitor_mod():
    spec = importlib.util.spec_from_file_location("monitor_script_nov", RUTA_MONITOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo.contar_instancias()
    return modulo


@pytest.fixture
def entorno(tmp_path, monkeypatch, monitor_mod):
    monkeypatch.setattr(bitacora, "LOG_DIR", tmp_path)
    monkeypatch.setattr(monitor_mod, "es_festivo", lambda d: False)  # en festivo el día sale "festivo", no "ausente"
    ruta = tmp_path / "employees.json"
    ruta.write_text(json.dumps({"employees": [
        {"id": "e1", "nombre": "Ana", "usuario": "ana@correo.test", "password": SECRETO, "activo": True},
        {"id": "e2", "nombre": "Luis", "usuario": "luis@correo.test", "password": SECRETO, "activo": True},
    ]}), encoding="utf-8")
    srv = monitor_mod.Monitor(("127.0.0.1", 0), None, ruta)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, ruta
    srv.shutdown()


def _post(srv, cuerpo):
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=30)
    c.request("POST", "/api/accion", body=json.dumps(cuerpo), headers={"Content-Type": "application/json", **OK})
    r = c.getresponse()
    return r.status, json.loads(r.read().decode("utf-8"))


def _hoy():
    return datetime.now().date().isoformat()


def test_monitor_guarda_una_novedad_y_la_muestra_sin_tocar_employees_json(monitor_mod, entorno):
    srv, ruta = entorno
    antes = ruta.read_bytes()
    estado, cuerpo = _post(srv, {"accion": "novedad", "op": "agregar", "emp_id": "e1", "tipo": "ausencia",
                                 "desde": _hoy(), "hasta": None, "motivo": "vacaciones"})
    assert (estado, cuerpo["ok"]) == (200, True), cuerpo
    assert ruta.read_bytes() == antes  # employees.json intacto
    guardado = (ruta.parent / "novedades.json").read_text(encoding="utf-8")
    assert SECRETO not in guardado and "ana@correo.test" not in guardado

    datos = monitor_mod.leer_estado(ruta)
    ana = next(f for f in datos["empleados"] if f["id"] == "e1")
    assert [n["motivo"] for n in ana["novedades"]] == ["vacaciones"]
    if datetime.now().weekday() != 6:  # en domingo no hay jornada que eximir
        assert ana["dia"] == "ausente (vacaciones)"
    assert any(e["tipo"] == "novedad" and e["operacion"] == "agregada" and e["emp_id"] == "e1"
               for e in bitacora.leer_eventos())


def test_monitor_rechaza_datos_invalidos_y_no_escribe(entorno):
    srv, ruta = entorno
    estado, cuerpo = _post(srv, {"accion": "novedad", "op": "agregar", "emp_id": "e1", "tipo": "ausencia",
                                 "desde": "2026-12-10", "hasta": "2026-12-01"})
    assert estado == 400 and "anterior" in cuerpo["mensaje"]
    assert _post(srv, {"accion": "novedad", "op": "agregar", "emp_id": "nadie", "tipo": "ausencia", "desde": _hoy()})[0] == 400
    assert _post(srv, {"accion": "novedad", "op": "borrar_todo"})[0] == 400
    assert not (ruta.parent / "novedades.json").exists()


def test_monitor_quitar_y_reactivar(entorno):
    srv, ruta = entorno
    _, cuerpo = _post(srv, {"accion": "novedad", "op": "agregar", "emp_id": "e2", "tipo": "desactivado"})
    (n,), _ = nov.leer(ruta.parent / "novedades.json")
    estado, cuerpo = _post(srv, {"accion": "novedad", "op": "terminar", "id": n["id"]})
    assert estado == 409 and cuerpo["bloqueado"]  # afecta a hoy: exige confirmar
    estado, cuerpo = _post(srv, {"accion": "novedad", "op": "terminar", "id": n["id"], "forzar": True})
    assert (estado, cuerpo["ok"]) == (200, True)
    assert nov.leer(ruta.parent / "novedades.json")[0] == []


def test_desactivar_a_quien_ya_marco_entrada_exige_confirmar(monitor_mod, entorno, monkeypatch):
    srv, ruta = entorno
    real = monitor_mod.leer_estado

    def con_entrada(ruta_emp=None, ahora=None):
        estado = real(ruta_emp, ahora)
        for f in estado["empleados"]:
            f["entrada"], f["salida"] = {"hora": "07:01:10"}, {"hora": None}
        return estado

    monkeypatch.setattr(monitor_mod, "leer_estado", con_entrada)
    pedido = {"accion": "novedad", "op": "agregar", "emp_id": "e1", "tipo": "desactivado"}
    estado, cuerpo = _post(srv, pedido)
    assert estado == 409 and "salida" in cuerpo["mensaje"]
    assert not (ruta.parent / "novedades.json").exists()
    assert _post(srv, {**pedido, "forzar": True})[0] == 200
    assert any(e["tipo"] == "novedad" and e["forzado"] for e in bitacora.leer_eventos())


def test_novedades_ilegibles_ponen_el_monitor_en_critico(monitor_mod, entorno):
    _, ruta = entorno
    (ruta.parent / "novedades.json").write_text("{ roto", encoding="utf-8")
    datos = monitor_mod.leer_estado(ruta)
    assert datos["nivel"] == "critico" and "ilegible" in datos["mensajes"][0]["texto"]


def test_la_actividad_describe_la_novedad():
    from src import estado_monitor as em
    d = em.describir({"tipo": "novedad", "ts": "2026-11-23T10:00:00", "nombre": "Ana", "operacion": "agregada",
                      "motivo": "vacaciones", "desde": "2026-12-20", "hasta": None})
    assert d["texto"] == "Novedad guardada: vacaciones (2026-12-20 → sin fin)" and d["nivel"] == "aviso"


def test_la_pagina_trae_el_panel_de_novedades(monitor_mod):
    assert 'id="nov"' in monitor_mod.PAGINA and '"novedad"' in monitor_mod.PAGINA
    assert "innerHTML" not in monitor_mod.PAGINA  # el motivo lo escribe una persona: solo textContent
