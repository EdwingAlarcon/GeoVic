"""Tests para src/empleados.py — carga y validación de configuración."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.empleados import _HORARIO_DEFAULT, _validar_empleado, cargar_empleados

EMPLOYEES_FILE = Path(__file__).parent.parent / "config" / "employees.json"


# ---------------------------------------------------------------------------
# Validación de campos requeridos
# ---------------------------------------------------------------------------

class TestValidarEmpleado:
    def test_empleado_valido_no_lanza(self):
        _validar_empleado({"id": "e1", "nombre": "Juan", "usuario": "jj", "password": "pw"})

    @pytest.mark.parametrize("campo", ["id", "nombre", "usuario", "password"])
    def test_campo_faltante_lanza(self, campo: str):
        emp = {"id": "e1", "nombre": "Juan", "usuario": "jj", "password": "pw"}
        del emp[campo]
        with pytest.raises(ValueError, match=campo):
            _validar_empleado(emp)

    @pytest.mark.parametrize("campo", ["id", "nombre", "usuario", "password"])
    def test_campo_vacio_lanza(self, campo: str):
        emp = {"id": "e1", "nombre": "Juan", "usuario": "jj", "password": "pw", campo: ""}
        with pytest.raises(ValueError, match=campo):
            _validar_empleado(emp)


# ---------------------------------------------------------------------------
# Carga desde employees.json
# ---------------------------------------------------------------------------

class TestCargarEmpleados:
    def test_carga_desde_json(self, tmp_path, monkeypatch):
        employees_file = tmp_path / "employees.json"
        employees_file.write_text(
            json.dumps({
                "employees": [
                    {
                        "id": "e1",
                        "nombre": "Test User",
                        "usuario": "tuser",
                        "password": "tpass",
                        "activo": True,
                    }
                ]
            }),
            encoding="utf-8",
        )
        import src.empleados as mod
        monkeypatch.setattr(mod, "EMPLOYEES_FILE", employees_file)
        result = mod.cargar_empleados()
        assert len(result) == 1
        assert result[0]["id"] == "e1"

    def test_solo_empleados_activos(self, tmp_path, monkeypatch):
        employees_file = tmp_path / "employees.json"
        employees_file.write_text(
            json.dumps({
                "employees": [
                    {"id": "e1", "nombre": "Activo", "usuario": "u1", "password": "p1", "activo": True},
                    {"id": "e2", "nombre": "Inactivo", "usuario": "u2", "password": "p2", "activo": False},
                ]
            }),
            encoding="utf-8",
        )
        import src.empleados as mod
        monkeypatch.setattr(mod, "EMPLOYEES_FILE", employees_file)
        result = mod.cargar_empleados()
        assert len(result) == 1
        assert result[0]["id"] == "e1"

    def test_horario_default_aplicado(self, tmp_path, monkeypatch):
        employees_file = tmp_path / "employees.json"
        employees_file.write_text(
            json.dumps({
                "employees": [
                    {"id": "e1", "nombre": "Test", "usuario": "u", "password": "p", "activo": True}
                ]
            }),
            encoding="utf-8",
        )
        import src.empleados as mod
        monkeypatch.setattr(mod, "EMPLOYEES_FILE", employees_file)
        result = mod.cargar_empleados()
        horario = result[0]["horario"]
        for k, v in _HORARIO_DEFAULT.items():
            assert horario[k] == v, f"Default faltante para '{k}'"

    def test_horario_personalizado_no_sobreescrito(self, tmp_path, monkeypatch):
        employees_file = tmp_path / "employees.json"
        employees_file.write_text(
            json.dumps({
                "employees": [
                    {
                        "id": "e1",
                        "nombre": "Test",
                        "usuario": "u",
                        "password": "p",
                        "activo": True,
                        "horario": {"entrada_semana_hora": 9},
                    }
                ]
            }),
            encoding="utf-8",
        )
        import src.empleados as mod
        monkeypatch.setattr(mod, "EMPLOYEES_FILE", employees_file)
        result = mod.cargar_empleados()
        assert result[0]["horario"]["entrada_semana_hora"] == 9

    def test_sin_empleados_activos_lanza(self, tmp_path, monkeypatch):
        employees_file = tmp_path / "employees.json"
        employees_file.write_text(
            json.dumps({"employees": [{"id": "e1", "nombre": "X", "usuario": "u", "password": "p", "activo": False}]}),
            encoding="utf-8",
        )
        import src.empleados as mod
        monkeypatch.setattr(mod, "EMPLOYEES_FILE", employees_file)
        with pytest.raises(ValueError, match="activos"):
            mod.cargar_empleados()

    def test_fallback_a_env(self, tmp_path, monkeypatch):
        import src.empleados as mod
        # Apuntar a archivo inexistente para forzar fallback
        monkeypatch.setattr(mod, "EMPLOYEES_FILE", tmp_path / "nonexistent.json")
        monkeypatch.setenv("GEOVICTORIA_USER", "envuser")
        monkeypatch.setenv("GEOVICTORIA_PASSWORD", "envpass")
        result = mod.cargar_empleados()
        assert len(result) == 1
        assert result[0]["id"] == "default"
        assert result[0]["usuario"] == "envuser"

    def test_fallback_sin_env_lanza(self, tmp_path, monkeypatch):
        import src.empleados as mod
        monkeypatch.setattr(mod, "EMPLOYEES_FILE", tmp_path / "nonexistent.json")
        # load_dotenv() leería el .env real del disco; lo neutralizamos
        monkeypatch.setattr(mod, "load_dotenv", lambda: None)
        monkeypatch.delenv("GEOVICTORIA_USER", raising=False)
        monkeypatch.delenv("GEOVICTORIA_PASSWORD", raising=False)
        with pytest.raises(ValueError):
            mod.cargar_empleados()
