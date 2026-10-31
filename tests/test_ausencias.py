"""Tests de "ausencias" (vacaciones, licencias): quien está exento no se marca, no alarma y no se reintenta."""
import json
from datetime import date, datetime

import pytest

from src import empleados as emps
from src import estado_monitor as em

LUNES = datetime(2026, 10, 26, 9, 40, 0)


def empleado(*ausencias, **extra):
    return {"id": "e1", "nombre": "Ana", "activo": True, "ausencias": list(ausencias),
            "horario": {"entrada_semana_hora": 8, "entrada_semana_minuto": 0,
                        "salida_semana_hora": 17, "salida_semana_minuto": 0,
                        "entrada_sabado_hora": 8, "entrada_sabado_minuto": 0,
                        "salida_sabado_hora": 13, "salida_sabado_minuto": 0}, **extra}


# --- ausencia_en --------------------------------------------------------------

def test_los_extremos_del_rango_son_inclusivos():
    e = empleado({"desde": "2026-11-10", "hasta": "2026-11-21", "motivo": "vacaciones"})
    assert emps.ausencia_en(e, date(2026, 11, 9)) is None
    assert emps.ausencia_en(e, date(2026, 11, 10)) == "vacaciones"
    assert emps.ausencia_en(e, date(2026, 11, 15)) == "vacaciones"
    assert emps.ausencia_en(e, date(2026, 11, 21)) == "vacaciones"
    assert emps.ausencia_en(e, date(2026, 11, 22)) is None  # se reincorpora solo


def test_sin_hasta_la_ausencia_no_termina():
    e = empleado({"desde": "2026-11-10", "motivo": "licencia"})
    assert emps.ausencia_en(e, date(2026, 11, 9)) is None
    assert emps.ausencia_en(e, date(2031, 1, 1)) == "licencia"


def test_un_solo_dia_y_motivo_por_defecto():
    e = empleado({"desde": "2026-12-01", "hasta": "2026-12-01"})
    assert emps.ausencia_en(e, date(2026, 12, 1)) == "ausencia"
    assert emps.ausencia_en(e, date(2026, 12, 2)) is None


def test_varias_ausencias_se_evaluan_todas():
    e = empleado({"desde": "2026-11-02", "hasta": "2026-11-03", "motivo": "cita"},
                 {"desde": "2026-12-01", "hasta": "2026-12-05", "motivo": "vacaciones"})
    assert emps.ausencia_en(e, date(2026, 11, 3)) == "cita"
    assert emps.ausencia_en(e, date(2026, 12, 4)) == "vacaciones"
    assert emps.ausencia_en(e, date(2026, 11, 20)) is None


@pytest.mark.parametrize("mala", [
    {"hasta": "2026-11-21"},                                   # sin desde
    {"desde": "10/11/2026", "hasta": "2026-11-21"},            # formato no ISO
    {"desde": "2026-11-10", "hasta": "pronto"},                # hasta ilegible
    {"desde": "2026-11-21", "hasta": "2026-11-10"},            # hasta anterior a desde
    "vacaciones", None, 7,
])
def test_una_entrada_mal_escrita_se_ignora_y_se_avisa(mala):
    e = empleado(mala)
    assert emps.ausencia_en(e, date(2026, 11, 15)) is None
    assert len(emps.ausencias_invalidas(e)) == 1


def test_sin_ausencias_o_con_un_valor_raro_no_falla():
    assert emps.ausencia_en({"id": "x"}, date(2026, 11, 15)) is None
    assert emps.ausencia_en({"ausencias": "vacaciones"}, date(2026, 11, 15)) is None
    assert emps.ausencias_invalidas({"id": "x"}) == []
    assert emps.ausencias_invalidas({"ausencias": "vacaciones"}) == ['"vacaciones"']


def test_una_entrada_mala_no_anula_a_las_buenas():
    e = empleado({"desde": "mal"}, {"desde": "2026-11-10", "hasta": "2026-11-21", "motivo": "vacaciones"})
    assert emps.ausencia_en(e, date(2026, 11, 15)) == "vacaciones"


# --- ausencia_vigente: relee el archivo ---------------------------------------

def test_vigente_ve_las_vacaciones_agregadas_sin_reiniciar(tmp_path, monkeypatch):
    archivo = tmp_path / "employees.json"
    monkeypatch.setattr(emps, "EMPLOYEES_FILE", archivo)
    cargado_al_arrancar = empleado()
    archivo.write_text(json.dumps({"employees": [
        empleado({"desde": "2026-11-10", "hasta": "2026-11-21", "motivo": "vacaciones"})]}), encoding="utf-8")
    assert emps.ausencia_en(cargado_al_arrancar, date(2026, 11, 12)) is None
    assert emps.ausencia_vigente(cargado_al_arrancar, date(2026, 11, 12)) == "vacaciones"


def test_vigente_ve_las_vacaciones_quitadas(tmp_path, monkeypatch):
    archivo = tmp_path / "employees.json"
    monkeypatch.setattr(emps, "EMPLOYEES_FILE", archivo)
    archivo.write_text(json.dumps({"employees": [empleado()]}), encoding="utf-8")
    con_ausencia = empleado({"desde": "2026-11-10", "motivo": "vacaciones"})
    assert emps.ausencia_vigente(con_ausencia, date(2026, 11, 12)) is None


@pytest.mark.parametrize("contenido", [None, "{ esto no es json"])
def test_vigente_sin_archivo_legible_usa_lo_cargado(tmp_path, monkeypatch, contenido):
    archivo = tmp_path / "employees.json"
    if contenido is not None:
        archivo.write_text(contenido, encoding="utf-8")
    monkeypatch.setattr(emps, "EMPLOYEES_FILE", archivo)
    e = empleado({"desde": "2026-11-10", "motivo": "licencia"})
    assert emps.ausencia_vigente(e, date(2026, 11, 12)) == "licencia"


# --- monitor ------------------------------------------------------------------

def _estado(empleados, ahora=LUNES):
    return em.calcular_estado(ahora, empleados, {}, [], {
        "pid": 1, "inicio": "2026-10-26T07:00:00", "fase": "activo", "plan": {},
        "ts": ahora.isoformat(timespec="seconds"), "tick_scheduler": ahora.isoformat(timespec="seconds")})


def test_el_ausente_no_esta_vencido_ni_se_ofrece_para_marcar():
    ausente = empleado({"desde": "2026-10-20", "hasta": "2026-10-30", "motivo": "vacaciones"})
    e = _estado([ausente])  # son las 9:40 y su entrada era a las 8:00: sin ausencia estaría VENCIDA
    fila = e["empleados"][0]
    assert fila["dia"] == "ausente (vacaciones)" and fila["entrada"] is None and fila["salida"] is None
    assert e["nivel"] == "ok"
    assert e["resumen"]["empleados"] == 0
    assert em.pendientes_de_marcar(e) == []


def test_el_monitor_lista_a_los_ausentes_para_que_un_error_de_fecha_se_vea():
    otro = {**empleado(), "id": "e2", "nombre": "Luis"}
    e = _estado([empleado({"desde": "2026-10-26", "motivo": "licencia"}), otro])
    textos = [m["texto"] for m in e["mensajes"]]
    assert any("Ausentes hoy" in t and "Ana (licencia)" in t and "Luis" not in t for t in textos)


def test_sin_ausencia_vigente_hoy_el_empleado_se_vigila_igual():
    pasada = empleado({"desde": "2026-10-01", "hasta": "2026-10-10", "motivo": "vacaciones"})
    e = _estado([pasada])
    assert e["empleados"][0]["entrada"]["estado"] == "vencida"
    assert not any("Ausentes" in m["texto"] for m in e["mensajes"])


# --- programador: no marca, no abre el portal, no reintenta -------------------

@pytest.fixture
def prog(monkeypatch):
    from src import programador
    llamadas = []

    async def run_falso(*a, **k):
        llamadas.append(("run", a, k))
        return "Entrada"

    async def verificar_falso(*a, **k):
        llamadas.append(("verificar", a, k))
        return "Salida"

    monkeypatch.setattr(programador, "run", run_falso)
    monkeypatch.setattr(programador, "verificar_estado", verificar_falso)
    monkeypatch.setattr(programador, "es_festivo", lambda d: False)
    monkeypatch.setattr(programador, "ausencia_vigente",
                        lambda emp, dia: "vacaciones" if emp["id"] == "ausente" else None)
    monkeypatch.setattr(programador, "ya_se_ejecuto_hoy", lambda *a: False)
    monkeypatch.setattr(programador, "tiempo_desde_ultimo_marcaje", lambda *a: 10 ** 6)
    monkeypatch.setattr(programador.bitacora, "registrar", lambda *a, **k: None)
    # Nada de esto debe escribir en src/logs (el id "presente" dejaría un registro_presente.json real)
    monkeypatch.setattr(programador, "guardar_registro", lambda *a, **k: None)
    monkeypatch.setattr(programador, "alertar_fallo", lambda *a, **k: None)
    programador.llamadas = llamadas
    return programador


def _emp(id_):
    return {**empleado(), "id": id_, "nombre": id_}


@pytest.mark.parametrize("funcion", ["entrada_semana_emp", "salida_semana_emp", "entrada_sabado_emp",
                                     "salida_sabado_emp", "verificar_pendientes_emp"])
def test_ningun_job_toca_el_portal_de_un_ausente(prog, funcion):
    getattr(prog, funcion)(_emp("ausente"))
    assert prog.llamadas == []


def test_el_marcaje_directo_y_el_reintento_tambien_lo_respetan(prog):
    assert prog.ejecutar_marcaje_emp(_emp("ausente"), "ENTRADA SEMANA (L-V)", validar_horario=False) is None
    prog.reintentar_marcaje_emp(_emp("ausente"), "ENTRADA SEMANA (L-V)", "Entrada", 1)
    assert prog.llamadas == []


def test_contraste_el_presente_si_llega_al_portal(prog):
    prog.salida_semana_emp(_emp("presente"))  # sin entrada previa local: consulta el portal
    assert [l[0] for l in prog.llamadas][:1] == ["verificar"]


def test_el_guardia_es_solo_para_el_ausente(prog):
    assert prog._ausente_hoy(_emp("ausente")) is True
    assert prog._ausente_hoy(_emp("presente")) is False
