"""Tests de reemplazos temporales: alguien que no estaba en el sistema cubre unos días el turno de otro.

Dentro del periodo el reemplazo marca con el horario del cubierto y el cubierto queda ausente; fuera
del periodo el reemplazo no marca. Un bloque mal escrito deja al reemplazo sin marcar (nunca al revés).
Ids propios (r*/c*) para no cruzarse con la última lectura que guarda empleados en memoria.
"""
import json
from datetime import date, datetime

import pytest

from src import empleados as emps
from src import estado_monitor as em

HORARIO_C = {"entrada_semana_hora": 6, "entrada_semana_minuto": 30, "salida_semana_hora": 15, "salida_semana_minuto": 0,
             "entrada_sabado_hora": 6, "entrada_sabado_minuto": 30, "salida_sabado_hora": 12, "salida_sabado_minuto": 0,
             "trabaja_sabados": False}


def cubierto(**extra):
    return {"id": "c1", "nombre": "Carla", "usuario": "c", "password": "x", "activo": True, "horario": dict(HORARIO_C), **extra}


def reemplazo(desde="2026-12-01", hasta="2026-12-05", **extra):
    return {"id": "r1", "nombre": "Rubén", "usuario": "r", "password": "y", "activo": True,
            "reemplazo": {"cubre_a": "c1", "desde": desde, "hasta": hasta}, **extra}


def resuelto(todos, emp_id):
    return next(e for e in emps.resolver_reemplazos(todos) if e["id"] == emp_id)


# --- reemplazo_de ----------------------------------------------------------------

@pytest.mark.parametrize("bloque, texto", [
    ("c1", "objeto"),
    ({"desde": "2026-12-01", "hasta": "2026-12-05"}, "cubre_a"),
    ({"cubre_a": "nadie", "desde": "2026-12-01", "hasta": "2026-12-05"}, "no existe"),
    ({"cubre_a": "r1", "desde": "2026-12-01", "hasta": "2026-12-05"}, "sí mismo"),
    ({"cubre_a": "c1", "desde": "2026-12-01"}, "obligatorios"),
    ({"cubre_a": "c1", "desde": "01/12/2026", "hasta": "2026-12-05"}, "obligatorios"),
    ({"cubre_a": "c1", "desde": "2026-12-05", "hasta": "2026-12-01"}, "anterior"),
])
def test_bloques_mal_escritos_se_detectan(bloque, texto):
    r = emps.reemplazo_de({"id": "r1", "reemplazo": bloque}, ["c1", "r1"])
    assert texto in r["invalido"]


def test_quien_no_es_reemplazo_no_cambia():
    assert emps.reemplazo_de(cubierto()) is None
    assert resuelto([cubierto()], "c1") == cubierto()


# --- horario y ausencias deducidas -------------------------------------------------

def test_el_reemplazo_toma_el_horario_de_quien_cubre():
    r = resuelto([cubierto(), reemplazo()], "r1")
    assert r["horario"] == HORARIO_C
    r["horario"]["entrada_semana_hora"] = 99  # es una copia: no altera al cubierto
    assert resuelto([cubierto(), reemplazo()], "c1")["horario"]["entrada_semana_hora"] == 6


def test_un_horario_propio_del_reemplazo_manda():
    propio = {"entrada_semana_hora": 10}
    assert resuelto([cubierto(), reemplazo(horario=propio)], "r1")["horario"] == propio


def test_el_reemplazo_solo_marca_dentro_de_su_periodo():
    r = resuelto([cubierto(), reemplazo()], "r1")
    assert emps.ausencia_en(r, date(2026, 11, 30)) == "reemplazo: empieza el 2026-12-01"
    assert emps.ausencia_en(r, date(2026, 12, 1)) is None
    assert emps.ausencia_en(r, date(2026, 12, 5)) is None
    assert emps.ausencia_en(r, date(2026, 12, 6)) == "reemplazo: terminó el 2026-12-05"
    assert emps.ausencias_invalidas(r) == []  # las ausencias deducidas están bien formadas


def test_el_cubierto_queda_ausente_solo_durante_el_periodo():
    c = resuelto([cubierto(), reemplazo()], "c1")
    assert emps.ausencia_en(c, date(2026, 11, 30)) is None
    assert emps.ausencia_en(c, date(2026, 12, 3)) == "cubierto por Rubén"
    assert emps.ausencia_en(c, date(2026, 12, 6)) is None


def test_las_ausencias_propias_del_cubierto_se_conservan():
    c = resuelto([cubierto(ausencias=[{"desde": "2026-12-20", "motivo": "vacaciones"}]), reemplazo()], "c1")
    assert emps.ausencia_en(c, date(2026, 12, 3)) == "cubierto por Rubén"
    assert emps.ausencia_en(c, date(2026, 12, 21)) == "vacaciones"


def test_un_reemplazo_mal_escrito_no_marca_nunca_y_el_cubierto_sigue_normal():
    todos = [cubierto(), reemplazo(hasta="pronto")]
    assert emps.ausencia_en(resuelto(todos, "r1"), date(2026, 12, 3)).startswith("reemplazo mal configurado")
    assert emps.ausencia_en(resuelto(todos, "c1"), date(2026, 12, 3)) is None
    assert [motivo for _, motivo in emps.reemplazos_invalidos(todos)] == ["'desde' y 'hasta' son obligatorios (AAAA-MM-DD)"]


def test_cubre_a_alguien_inactivo_tambien_vale():
    r = resuelto([cubierto(activo=False), reemplazo()], "r1")
    assert r["horario"] == HORARIO_C


# --- cargar_empleados y ausencia_vigente (lo que usa el programador) ------------------

@pytest.fixture
def archivo(tmp_path, monkeypatch):
    ruta = tmp_path / "employees.json"
    monkeypatch.setattr(emps, "EMPLOYEES_FILE", ruta)

    def escribir(*empleados):
        ruta.write_text(json.dumps({"employees": list(empleados)}), encoding="utf-8")
    return escribir


def test_cargar_empleados_programa_al_reemplazo_con_el_horario_cubierto(archivo):
    archivo(cubierto(), reemplazo())
    cargados = {e["id"]: e for e in emps.cargar_empleados()}
    assert cargados["r1"]["horario"]["entrada_semana_hora"] == 6
    assert cargados["r1"]["horario"]["entrada_semana_minuto"] == 30


def test_ausencia_vigente_aplica_el_reemplazo_y_relee_las_fechas_sin_reiniciar(archivo):
    archivo(cubierto(), reemplazo())
    c, r = cubierto(), reemplazo()  # como quedaron cargados al arrancar
    assert emps.ausencia_vigente(c, date(2026, 12, 3)) == "cubierto por Rubén"
    assert emps.ausencia_vigente(r, date(2026, 12, 3)) is None
    archivo(cubierto(), reemplazo(hasta="2026-12-02"))  # se acorta el reemplazo sin reiniciar
    assert emps.ausencia_vigente(c, date(2026, 12, 3)) is None
    assert emps.ausencia_vigente(r, date(2026, 12, 3)) == "reemplazo: terminó el 2026-12-02"


def test_con_el_archivo_ilegible_se_usa_la_ultima_lista_buena(archivo, tmp_path):
    archivo(cubierto(), reemplazo())
    assert emps.ausencia_vigente(cubierto(), date(2026, 12, 3)) == "cubierto por Rubén"
    (tmp_path / "employees.json").write_text("{ roto", encoding="utf-8")
    assert emps.ausencia_vigente(cubierto(), date(2026, 12, 3)) == "cubierto por Rubén"
    assert emps.ausencia_vigente(reemplazo(), date(2026, 12, 9)) == "reemplazo: terminó el 2026-12-05"


# --- monitor ---------------------------------------------------------------------------

def test_monitor_ni_vencida_para_el_cubierto_ni_para_el_reemplazo_fuera_de_periodo():
    lunes = datetime(2026, 12, 7, 10, 0)  # el reemplazo r2 terminó el viernes 5
    todos = emps.resolver_reemplazos([cubierto(), reemplazo(desde="2026-12-07", hasta="2026-12-11"),
                                      {**reemplazo(), "id": "r2", "nombre": "Sara"}])
    latido = {"pid": 1, "fase": "activo", "plan": {}, "ts": lunes.isoformat(), "tick_scheduler": lunes.isoformat()}
    estado = em.calcular_estado(lunes, todos, {}, [], latido)
    filas = {f["id"]: f for f in estado["empleados"]}
    assert filas["c1"]["dia"] == "ausente (cubierto por Rubén)"
    assert filas["r1"]["entrada"]["estado"] == "vencida"  # en su periodo sí se vigila (aquí sin marcaje)
    assert filas["r1"]["entrada"]["programada"] == "06:30:00"  # con el horario de Carla
    assert filas["r2"]["dia"].startswith("ausente (reemplazo: terminó")
