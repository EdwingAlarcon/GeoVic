"""Contraseñas cifradas con DPAPI (src/credenciales.py) y su migración (scripts/cifrar_credenciales.py)."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from src import credenciales, diagnostico_login as dl
from src.geovictoria import get_credentials

solo_windows = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI solo existe en Windows")
CLAVE = "Cl@ve-Ñandú 2026"


def _script():
    ruta = Path(__file__).parent.parent / "scripts" / "cifrar_credenciales.py"
    spec = importlib.util.spec_from_file_location("cifrar_credenciales", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_texto_plano_sigue_funcionando():
    assert credenciales.revelar("en-claro") == "en-claro"
    assert credenciales.revelar(None) == "" and not credenciales.esta_cifrada("en-claro")
    assert get_credentials({"usuario": "u", "password": "en-claro"}) == ("u", "en-claro")


@solo_windows
def test_ida_y_vuelta_y_no_contiene_la_clave():
    cifrada = credenciales.proteger(CLAVE)
    assert cifrada.startswith("dpapi:") and CLAVE not in cifrada
    assert credenciales.revelar(cifrada) == CLAVE
    assert credenciales.proteger(cifrada) == cifrada  # idempotente
    assert get_credentials({"usuario": "u", "password": cifrada}) == ("u", CLAVE)
    assert dl.con_password_en_claro({"id": "e1", "password": cifrada})["password"] == CLAVE


@pytest.mark.parametrize("valor", ["dpapi:no-es-base64!!", "dpapi:" + "QUJD" * 10])
def test_blob_danado_falla_con_error_claro(valor):
    with pytest.raises(credenciales.CredencialIlegible, match="equipo donde se cifró"):
        credenciales.revelar(valor)
    with pytest.raises(ValueError):  # probar_login lo captura como ValueError
        dl.con_password_en_claro({"id": "e1", "password": valor})


@solo_windows
def test_migracion_cifra_conserva_el_resto_y_es_idempotente(tmp_path):
    ruta = tmp_path / "employees.json"
    original = {"employees": [
        {"id": "e1", "nombre": "Ána", "usuario": "ana@x.test", "password": CLAVE, "activo": True,
         "horario": {"entrada_semana_hora": 7}, "ausencias": [{"desde": "2026-12-01", "motivo": "vacaciones"}]},
        {"id": "e2", "nombre": "Luis", "usuario": "luis@x.test", "password": "otra", "activo": False,
         "reemplazo": {"cubre_a": "e1", "desde": "2026-12-01", "hasta": "2026-12-05"}},
    ]}
    ruta.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
    script = _script()

    assert script.cifrar_archivo(ruta, solo_revisar=True) == (2, 0)
    assert json.loads(ruta.read_text(encoding="utf-8")) == original  # revisar no escribe

    assert script.cifrar_archivo(ruta) == (2, 0)
    texto = ruta.read_text(encoding="utf-8")
    assert CLAVE not in texto and '"otra"' not in texto and "Ána" in texto  # ensure_ascii=False
    nuevo = json.loads(texto)
    for antes, despues in zip(original["employees"], nuevo["employees"]):
        assert credenciales.revelar(despues["password"]) == antes["password"]
        assert {k: v for k, v in despues.items() if k != "password"} == {k: v for k, v in antes.items() if k != "password"}

    assert script.cifrar_archivo(ruta) == (0, 2)  # segunda vez: nada que hacer
    assert json.loads(ruta.read_text(encoding="utf-8")) == nuevo
    assert not list(tmp_path.glob(".employees_*.tmp"))


def test_migracion_no_escribe_si_hay_un_blob_ilegible(tmp_path):
    ruta = tmp_path / "employees.json"
    datos = {"employees": [{"id": "e1", "password": "en-claro"}, {"id": "e2", "password": "dpapi:QUJD"}]}
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(credenciales.CredencialIlegible):
        _script().cifrar_archivo(ruta)
    assert json.loads(ruta.read_text(encoding="utf-8")) == datos
