"""Tests de reintentos: cuándo se insiste en un marcaje que el portal no registró."""
from datetime import datetime, time

from src import reintentos as r

PROG = time(16, 0, 0)


def ahora(h, m=0):
    return datetime(2026, 10, 26, h, m, 0)


def test_reintenta_dentro_de_la_ventana_y_del_tope():
    assert r.puede_reintentar(ahora(16, 5), PROG, 1, 2) == (True, "")
    assert r.puede_reintentar(ahora(16, 30), PROG, 2, 2) == (True, "")


def test_no_reintenta_si_se_agotaron_los_reintentos_o_estan_desactivados():
    ok, motivo = r.puede_reintentar(ahora(16, 5), PROG, 3, 2)
    assert not ok and "agotaron" in motivo
    ok, motivo = r.puede_reintentar(ahora(16, 5), PROG, 1, 0)
    assert not ok and "desactivados" in motivo


def test_no_reintenta_muy_tarde_ni_antes_de_la_ventana():
    ok, motivo = r.puede_reintentar(ahora(18, 5), PROG, 1, 2)  # 2 h 5 min después
    assert not ok and "120" in motivo
    assert r.puede_reintentar(ahora(18, 0), PROG, 1, 2)[0]       # justo en el límite
    ok, motivo = r.puede_reintentar(ahora(15, 0), PROG, 1, 2)    # una hora antes
    assert not ok and "hora" in motivo


def test_entorno_valido_invalido_y_cero(monkeypatch):
    monkeypatch.delenv("GEOVICTORIA_REINTENTOS", raising=False)
    assert r.reintentos_desde_entorno() == 2
    monkeypatch.setenv("GEOVICTORIA_REINTENTOS", "0")
    assert r.reintentos_desde_entorno() == 0
    monkeypatch.setenv("GEOVICTORIA_REINTENTOS", "abc")
    assert r.reintentos_desde_entorno() == 2
    monkeypatch.setenv("GEOVICTORIA_REINTENTO_DEMORA", "20")
    assert r.demora_reintento_desde_entorno() == 20
    monkeypatch.setenv("GEOVICTORIA_REINTENTO_DEMORA", "-5")
    assert r.demora_reintento_desde_entorno() == 1
