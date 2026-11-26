"""scripts/cambiar_password.py: cambia la contraseña de UN empleado y la guarda cifrada."""
import base64
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from src import credenciales

CLAVE = "Nuev@-Ñandú 2026"


def _script():
    ruta = Path(__file__).parent.parent / "scripts" / "cambiar_password.py"
    spec = importlib.util.spec_from_file_location("cambiar_password", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def dpapi_falso(monkeypatch):
    """Cifrado reversible de pega para probar en cualquier sistema (DPAPI real: test_credenciales.py)."""
    def proteger(p):
        return p if credenciales.esta_cifrada(p) else "dpapi:" + base64.b64encode(p[::-1].encode()).decode()

    def revelar(v):
        if not credenciales.esta_cifrada(v):
            return v or ""
        return base64.b64decode(v[len("dpapi:"):]).decode()[::-1]

    monkeypatch.setattr(credenciales, "proteger", proteger)
    monkeypatch.setattr(credenciales, "revelar", revelar)
    return proteger


def _archivo(tmp_path, empleados):
    ruta = tmp_path / "employees.json"
    ruta.write_text(json.dumps({"employees": empleados}, ensure_ascii=False), encoding="utf-8")
    return ruta


def _base(proteger):
    return [
        {"id": "e1", "nombre": "Ána", "usuario": "ana@x.test", "password": proteger("vieja1"), "activo": True,
         "horario": {"entrada_semana_hora": 7}, "ausencias": [{"desde": "2026-12-01", "motivo": "vacaciones"}]},
        {"id": "e2", "nombre": "Luis", "usuario": "luis@x.test", "password": proteger("vieja2"), "activo": False},
    ]


def test_cambia_solo_ese_empleado_cifrada_y_conserva_el_resto(tmp_path, dpapi_falso):
    original = _base(dpapi_falso)
    ruta = _archivo(tmp_path, original)

    _script().guardar_password(ruta, "e1", CLAVE)

    texto = ruta.read_text(encoding="utf-8")
    assert CLAVE not in texto
    nuevos = json.loads(texto)["employees"]
    assert credenciales.revelar(nuevos[0]["password"]) == CLAVE
    assert nuevos[1] == original[1]
    assert {k: v for k, v in nuevos[0].items() if k != "password"} == \
        {k: v for k, v in original[0].items() if k != "password"}
    assert [p.name for p in tmp_path.iterdir()] == ["employees.json"]  # sin temporales


@pytest.mark.parametrize("emp_id", ["no-existe", "e1"])
def test_id_inexistente_o_repetido_no_escribe(tmp_path, dpapi_falso, emp_id):
    empleados = _base(dpapi_falso)
    if emp_id == "e1":
        empleados.append({**empleados[0]})
    ruta = _archivo(tmp_path, empleados)
    antes = ruta.read_bytes()
    with pytest.raises(ValueError, match="debe haber 1"):
        _script().guardar_password(ruta, emp_id, CLAVE)
    assert ruta.read_bytes() == antes


@pytest.mark.parametrize("nueva", ["", "dpapi:abc"])
def test_rechaza_vacia_o_con_prefijo(tmp_path, dpapi_falso, nueva):
    ruta = _archivo(tmp_path, _base(dpapi_falso))
    antes = ruta.read_bytes()
    with pytest.raises(ValueError):
        _script().guardar_password(ruta, "e1", nueva)
    assert ruta.read_bytes() == antes


def test_si_la_ida_y_vuelta_falla_no_escribe(tmp_path, dpapi_falso, monkeypatch):
    ruta = _archivo(tmp_path, _base(dpapi_falso))
    antes = ruta.read_bytes()
    monkeypatch.setattr(credenciales, "revelar", lambda v: "otra")
    with pytest.raises(ValueError, match="ida y vuelta"):
        _script().guardar_password(ruta, "e1", CLAVE)
    assert ruta.read_bytes() == antes


def test_pedir_clave_reintenta_si_no_coinciden_y_cancela_vacia():
    script = _script()
    respuestas = iter(["a", "b", CLAVE, CLAVE])
    assert script.pedir_clave_nueva(lambda _: next(respuestas)) == CLAVE
    assert script.pedir_clave_nueva(lambda _: "") == ""
    distintas = iter(["a", "b"] * script.INTENTOS_CLAVE)
    assert script.pedir_clave_nueva(lambda _: next(distintas)) == ""


def test_main_sin_probar_guarda_cifrada(tmp_path, dpapi_falso, monkeypatch, capsys):
    ruta = _archivo(tmp_path, _base(dpapi_falso))
    script = _script()
    monkeypatch.setattr(script.getpass, "getpass", lambda _: CLAVE)
    monkeypatch.setattr(sys, "argv", ["cambiar_password.py", "e2", "--sin-probar", "--empleados", str(ruta)])

    assert script.main() == 0
    assert credenciales.revelar(json.loads(ruta.read_text(encoding="utf-8"))["employees"][1]["password"]) == CLAVE
    salida = capsys.readouterr().out
    assert CLAVE not in salida and "reiniciar_programador" in salida
