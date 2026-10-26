"""Tests de estado_monitor: cada estado que muestra el monitor, con casos controlados."""
import json
from datetime import datetime, timedelta

import pytest

from src import estado_monitor as em

LUNES = datetime(2026, 10, 26, 9, 40, 0)  # lunes
DOMINGO = datetime(2026, 10, 25, 9, 40, 0)
SABADO = datetime(2026, 10, 24, 9, 40, 0)


def emp(id_="e1", nombre="Ana", entrada=(8, 0), salida=(17, 0), **extra):
    horario = {"entrada_semana_hora": entrada[0], "entrada_semana_minuto": entrada[1],
               "salida_semana_hora": salida[0], "salida_semana_minuto": salida[1]}
    return {"id": id_, "nombre": nombre, "activo": True, "horario": horario, **extra}


def registro(hora="2026-10-26T08:00:20", origen="programador", tipo="ENTRADA SEMANA (L-V)", dia="2026-10-26"):
    return {dia: {tipo: {"ejecutado": True, "hora": hora, "origen": origen}}}


def latido(ahora=LUNES, edad=10, fase="activo", tick=5, plan=None):
    return {"pid": 1234, "inicio": "2026-10-26T07:00:00", "fase": fase, "plan": plan or {},
            "ts": (ahora - timedelta(seconds=edad)).isoformat(timespec="seconds"),
            "tick_scheduler": (ahora - timedelta(seconds=tick)).isoformat(timespec="seconds")}


def estado(empleados, registros=None, eventos=None, lat="auto", **kw):
    ahora = kw.pop("ahora", LUNES)
    lat = latido(ahora) if lat == "auto" else lat
    return em.calcular_estado(ahora, empleados, registros or {}, eventos or [], lat, **kw)


def entrada(e):
    return e["empleados"][0]["entrada"]


# --- confirmacion_de ---------------------------------------------------------

@pytest.mark.parametrize("accion, boton, esperado", [
    ("Entrada", "Salida", True), ("Entrada", "Entrada", False), ("Entrada", None, None),
    ("Salida", "Entrada", True), ("Salida", "Salida", False), ("Salida", None, None),
    ("Entrada", "otra cosa", None),
])
def test_confirmacion_de(accion, boton, esperado):
    assert em.confirmacion_de(accion, boton) is esperado


# --- estados de un marcaje ---------------------------------------------------

def test_pendiente_antes_de_su_hora():
    e = estado([emp(entrada=(10, 0))])
    assert entrada(e)["estado"] == "pendiente" and entrada(e)["programada"] == "10:00:00"
    assert e["nivel"] == "ok"


def test_vencida_si_paso_su_hora_sin_marcaje():
    e = estado([emp(entrada=(8, 0))])
    assert entrada(e)["estado"] == "vencida"
    assert e["nivel"] == "critico" and any("VENCIDA" in m["texto"] for m in e["mensajes"])


def test_la_gracia_evita_dar_por_vencido_de_inmediato():
    plan = {"e1": {"mon": {"entrada": "09:38:00", "salida": "17:00:00"}}}   # hace 2 min, dentro de 3 min de gracia
    e = estado([emp()], lat=latido(plan=plan))
    assert entrada(e)["estado"] == "pendiente"


def test_usa_la_hora_con_segundos_del_plan_del_programador():
    plan = {"e1": {"mon": {"entrada": "08:30:40", "salida": "17:00:40"}}}
    antes = datetime(2026, 10, 26, 8, 31, 30)
    despues = datetime(2026, 10, 26, 8, 34, 0)
    assert entrada(estado([emp()], lat=latido(antes, plan=plan), ahora=antes))["estado"] == "pendiente"
    assert entrada(estado([emp()], lat=latido(despues, plan=plan), ahora=despues))["estado"] == "vencida"


def test_marcada_reciente_espera_confirmacion():
    e = estado([emp()], registros={"e1": registro(hora="2026-10-26T09:38:00")})
    assert entrada(e)["estado"] == "marcada" and "esperando" in entrada(e)["detalle"]


def test_marcada_antigua_sin_confirmar_lo_dice_sin_alarmar():
    e = estado([emp()], registros={"e1": registro(hora="2026-10-26T08:00:20")})
    assert entrada(e)["estado"] == "marcada" and "sin confirmación independiente" in entrada(e)["detalle"]
    assert e["nivel"] == "ok"


def test_confirmada_por_el_segundo_login():
    ev = [{"tipo": "confirmacion", "emp_id": "e1", "accion": "Entrada", "confirmada": True, "boton": "Salida"}]
    assert entrada(estado([emp()], {"e1": registro()}, ev))["estado"] == "confirmada"


def test_confirmada_si_el_origen_es_el_portal():
    assert entrada(estado([emp()], {"e1": registro(origen="portal")}))["estado"] == "confirmada"


def test_no_confirmada_es_critica():
    ev = [{"tipo": "confirmacion", "emp_id": "e1", "accion": "Entrada", "confirmada": False, "boton": "Entrada"}]
    e = estado([emp()], {"e1": registro()}, ev)
    assert entrada(e)["estado"] == "no_confirmada" and e["nivel"] == "critico"


def test_confirmacion_no_concluyente_deja_marcada():
    ev = [{"tipo": "confirmacion", "emp_id": "e1", "accion": "Entrada", "confirmada": None}]
    assert entrada(estado([emp()], {"e1": registro()}, ev))["estado"] == "marcada"


def test_duplicado_es_un_aviso():
    ev = [{"tipo": "marcaje", "emp_id": "e1", "esperada": "Entrada", "accion": "Entrada", "resultado": "ok"}] * 2
    e = estado([emp()], {"e1": registro()}, ev)
    assert entrada(e)["duplicada"] is True and entrada(e)["exitos"] == 2
    assert e["nivel"] == "aviso"


def test_los_eventos_de_otro_empleado_no_cuentan():
    ev = [{"tipo": "confirmacion", "emp_id": "OTRO", "accion": "Entrada", "confirmada": False}]
    assert entrada(estado([emp()], {"e1": registro()}, ev))["estado"] == "marcada"


# --- tipo de día -------------------------------------------------------------

def test_domingo_festivo_y_desactivado_no_esperan_marcajes():
    assert estado([emp()], ahora=DOMINGO)["empleados"][0]["dia"] == "domingo"
    f = estado([emp()], festivo=True)["empleados"][0]
    assert f["dia"] == "festivo" and f["entrada"] is None
    d = estado([emp(activo=False)])
    assert d["empleados"][0]["dia"] == "desactivado" and d["nivel"] == "ok"


def test_sabado_solo_si_trabaja_sabados():
    assert estado([emp()], ahora=SABADO)["empleados"][0]["dia"] == "sabado"
    no_trabaja = emp()
    no_trabaja["horario"]["trabaja_sabados"] = False
    assert estado([no_trabaja], ahora=SABADO)["empleados"][0]["dia"] == "no_trabaja"


# --- programador -------------------------------------------------------------

def test_programador_vivo():
    p = estado([emp(entrada=(10, 0))])["programador"]
    assert p["vivo"] is True and p["scheduler_ok"] is True and p["pid"] == 1234


def test_sin_latido_es_critico_en_dia_laboral():
    e = estado([emp(entrada=(10, 0))], lat=latido(edad=600))
    assert e["programador"]["vivo"] is False and e["nivel"] == "critico"
    e2 = estado([emp()], lat=None)
    assert e2["nivel"] == "critico" and any("no hay latido" in m["texto"] for m in e2["mensajes"])


def test_sin_latido_en_domingo_solo_avisa():
    assert estado([emp()], ahora=DOMINGO, lat=None)["nivel"] == "aviso"


def test_proceso_vivo_pero_scheduler_colgado_es_critico():
    e = estado([emp(entrada=(10, 0))], lat=latido(tick=600))
    assert e["programador"]["vivo"] is True and e["programador"]["scheduler_ok"] is False
    assert e["nivel"] == "critico" and "scheduler no responde" in e["mensajes"][0]["texto"]


def test_fase_arrancando_no_exige_scheduler():
    p = estado([emp(entrada=(10, 0))], lat=latido(fase="arrancando"))["programador"]
    assert p["vivo"] is True and p["scheduler_ok"] is None


def test_mas_de_una_instancia_es_aviso():
    e = estado([emp(entrada=(10, 0))], instancias=2)
    assert e["nivel"] == "aviso" and "2 instancias" in e["mensajes"][0]["texto"]


def test_cuenta_arranques_del_dia():
    ev = [{"tipo": "programador_inicio"}, {"tipo": "programador_inicio"}]
    assert estado([emp(entrada=(10, 0))], eventos=ev)["programador"]["arranques_hoy"] == 2


# --- login, actividad, alertas, privacidad -----------------------------------

def test_login_fallido_con_entrada_pendiente_avisa():
    ev = [{"tipo": "login", "emp_id": "e1", "ok": False, "motivo": "timeout", "ts": "2026-10-26T09:30:00"}]
    e = estado([emp(entrada=(10, 0))], eventos=ev)
    f = e["empleados"][0]
    assert f["login"]["ok"] is False and f["fallos_login"] == 1
    assert e["nivel"] == "aviso" and "timeout" in e["mensajes"][0]["texto"]


def test_actividad_mas_reciente_primero_y_limitada():
    ev = [{"tipo": "login", "emp_id": "e1", "nombre": "Ana", "ok": True, "ms": 900, "ts": f"2026-10-26T09:{i:02d}:00"}
          for i in range(40)]
    act = estado([emp(entrada=(10, 0))], eventos=ev)["actividad"]
    assert len(act) == 25 and act[0]["hora"] == "09:39:00" and "Login correcto" in act[0]["texto"]


def test_descripciones_de_eventos_clave():
    d = em.describir({"tipo": "login", "ok": False, "motivo": "timeout", "ts": "2026-10-26T09:00:00"})
    assert d["nivel"] == "error" and "FALLIDO" in d["texto"]
    assert em.describir({"tipo": "confirmacion", "accion": "Entrada", "confirmada": False, "boton": "Entrada"})["nivel"] == "error"
    assert em.describir({"tipo": "estado_portal", "boton": None})["texto"] == "El portal ofrece: ningún botón"


def test_alertas_por_usuario():
    alertas = [{"nombre": "Ana"}, {"nombre": "Ana"}, {"nombre": "Luis"}]
    a = estado([emp(entrada=(10, 0))], alertas_hoy=alertas)["alertas"]
    assert a == {"total": 3, "por_usuario": {"Ana": 2, "Luis": 1}}


def test_el_estado_jamas_incluye_credenciales():
    secreto = emp(usuario="ana@correo.test", password="S3cr3t0-Unico")
    e = estado([secreto], registros={"e1": registro()})
    texto = json.dumps(e, ensure_ascii=False)
    assert "S3cr3t0-Unico" not in texto and "ana@correo.test" not in texto


# --- Reconciliación de confirmaciones y bloqueo de reinicio ---------------------

def _conf(emp_id="e1", accion="Entrada", confirmada=True):
    return {"tipo": "confirmacion", "emp_id": emp_id, "accion": accion, "confirmada": confirmada}


def test_marcaje_del_programador_sin_confirmacion_se_reconcilia():
    hoy = registro()["2026-10-26"]
    assert em.marcajes_sin_confirmar(hoy, [], "e1") == [("ENTRADA SEMANA (L-V)", "Entrada")]


def test_no_se_reconcilia_lo_ya_confirmado_ni_lo_detectado_en_el_portal():
    assert em.marcajes_sin_confirmar(registro()["2026-10-26"], [_conf()], "e1") == []
    assert em.marcajes_sin_confirmar(registro()["2026-10-26"], [_conf(confirmada=False)], "e1") == []  # ya alertó
    assert em.marcajes_sin_confirmar(registro(origen="portal")["2026-10-26"], [], "e1") == []


def test_confirmacion_no_concluyente_o_de_otro_empleado_si_se_reconcilia():
    hoy = registro()["2026-10-26"]
    assert em.marcajes_sin_confirmar(hoy, [_conf(confirmada=None)], "e1")
    assert em.marcajes_sin_confirmar(hoy, [_conf(emp_id="e2")], "e1")


def test_marca_de_version_anterior_sin_origen_cuenta_como_del_programador():
    hoy = {"SALIDA SEMANA (L-V)": {"ejecutado": True, "hora": "2026-10-26T17:00:05"}}
    assert em.marcajes_sin_confirmar(hoy, [], "e1") == [("SALIDA SEMANA (L-V)", "Salida")]


def _estado_con(entrada):
    return {"empleados": [{"nombre": "Ana", "entrada": entrada, "salida": {"estado": "pendiente", "programada": "17:00:10"}}]}


def test_bloquea_reiniciar_justo_antes_y_durante_la_gracia_de_un_marcaje():
    ahora = datetime(2026, 10, 26, 8, 0, 0)
    for programada in ("08:01:00", "07:58:30"):  # faltan 60 s / pasaron 90 s sin registrarse
        assert "Ana" in em.bloqueo_por_marcaje(_estado_con({"estado": "pendiente", "programada": programada}), ahora)


def test_no_bloquea_lejos_de_un_marcaje_ni_cuando_ya_vencio():
    ahora = datetime(2026, 10, 26, 8, 0, 0)
    assert em.bloqueo_por_marcaje(_estado_con({"estado": "pendiente", "programada": "09:00:00"}), ahora) is None
    assert em.bloqueo_por_marcaje(_estado_con({"estado": "pendiente", "programada": "07:50:00"}), ahora) is None
    assert em.bloqueo_por_marcaje(_estado_con({"estado": "vencida", "programada": "07:50:00"}), ahora) is None


def test_bloquea_mientras_se_espera_la_confirmacion():
    ahora = datetime(2026, 10, 26, 8, 0, 0)
    e = {"estado": "marcada", "programada": "07:59:00", "detalle": "esperando confirmación del portal…"}
    assert "confirmando" in em.bloqueo_por_marcaje(_estado_con(e), ahora)
    e["detalle"] = "sin confirmación independiente"  # ya pasó la ventana: no bloquea
    assert em.bloqueo_por_marcaje(_estado_con(e), ahora) is None


def test_bloqueo_tolera_estado_con_error():
    assert em.bloqueo_por_marcaje({"error": "x"}, datetime(2026, 10, 26, 8, 0, 0)) is None
