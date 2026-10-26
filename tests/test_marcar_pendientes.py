"""Tests de scripts/marcar_pendientes.py: pares, ocupado y registro; nunca abre el portal."""
import importlib.util
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from src import bitacora

RUTA = Path(__file__).parent.parent / "scripts" / "marcar_pendientes.py"


@pytest.fixture(scope="module")
def mp():
    spec = importlib.util.spec_from_file_location("marcar_pendientes_script", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_parsea_pares_y_normaliza_la_accion(mp):
    assert mp.parsear_pares(["emp4:salida", "emp1:Entrada"]) == [("emp4", "Salida"), ("emp1", "Entrada")]
    assert mp.parsear_pares([]) == []


@pytest.mark.parametrize("malo", ["emp4", "emp4:", ":salida", "emp4:borrar", "emp4:salida:x"])
def test_rechaza_pares_invalidos(mp, malo):
    with pytest.raises(ValueError):
        mp.parsear_pares([malo])


def test_ocupado_solo_por_actividad_reciente_de_otro_proceso(mp):
    ahora = datetime(2026, 10, 26, 16, 10, 0)
    reciente = {"ts": "2026-10-26T16:09:30", "pid": 111, "tipo": "login", "emp_id": "e1"}
    assert mp.esta_ocupado([reciente], "e1", ahora, mi_pid=222)
    assert not mp.esta_ocupado([reciente], "e1", ahora, mi_pid=111)  # es mi propia actividad
    assert not mp.esta_ocupado([reciente], "e2", ahora, mi_pid=222)  # otro empleado
    assert not mp.esta_ocupado([{**reciente, "ts": "2026-10-26T16:05:00"}], "e1", ahora, mi_pid=222)  # vieja
    assert not mp.esta_ocupado([{**reciente, "tipo": "programador_inicio"}], "e1", ahora, mi_pid=222)


def test_tipo_de_marcaje_segun_el_dia(mp):
    assert mp.tipo_marcaje("Salida", date(2026, 10, 26)) == "SALIDA SEMANA (L-V)"   # lunes
    assert mp.tipo_marcaje("Entrada", date(2026, 10, 24)) == "ENTRADA SÁBADO"       # sábado


def test_guardar_registro_escribe_origen_y_se_puede_anular(mp, tmp_path, monkeypatch):
    monkeypatch.setattr(bitacora, "LOG_DIR", tmp_path)
    mp.guardar_registro("e1", "SALIDA SEMANA (L-V)", "manual")
    marca = json.loads((tmp_path / "registro_e1.json").read_text(encoding="utf-8"))[date.today().isoformat()]["SALIDA SEMANA (L-V)"]
    assert marca["ejecutado"] is True and marca["origen"] == "manual" and marca["variacion_minutos"] == 0

    mp.guardar_registro("e1", "SALIDA SEMANA (L-V)", "manual", ejecutado=False)
    marca = json.loads((tmp_path / "registro_e1.json").read_text(encoding="utf-8"))[date.today().isoformat()]["SALIDA SEMANA (L-V)"]
    assert marca["ejecutado"] is False
    assert not list(tmp_path.glob("*.tmp"))


def test_main_rechaza_pares_invalidos_sin_abrir_el_portal(mp, capsys):
    assert mp.main(["emp4:borrar"]) == 2
    assert "no válido" in capsys.readouterr().out.lower()
