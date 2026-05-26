"""
Carga y valida la configuración de empleados.
Soporta modo individual (.env) y multi-empleado (config/employees.json).
"""
import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

EMPLOYEES_FILE = Path(__file__).parent.parent / "config" / "employees.json"

_HORARIO_DEFAULT: Dict = {
    "entrada_semana_hora": 7,
    "entrada_semana_minuto": 0,
    "salida_semana_hora": 17,
    "salida_semana_minuto": 0,
    "entrada_sabado_hora": 7,
    "entrada_sabado_minuto": 0,
    "salida_sabado_hora": 13,
    "salida_sabado_minuto": 0,
    "trabaja_sabados": True,
}


def _validar_empleado(emp: Dict) -> None:
    for campo in ("id", "nombre", "usuario", "password"):
        if not emp.get(campo):
            raise ValueError(f"Empleado con campo faltante o vacío: '{campo}'")


def cargar_empleados() -> List[Dict]:
    """
    Carga empleados activos desde config/employees.json.
    Si el archivo no existe, crea un empleado único desde variables de entorno .env.
    """
    if EMPLOYEES_FILE.exists():
        with open(EMPLOYEES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        activos = [e for e in data.get("employees", []) if e.get("activo", True)]

        if not activos:
            raise ValueError("No hay empleados activos en config/employees.json")

        for emp in activos:
            _validar_empleado(emp)
            emp.setdefault("horario", {})
            for k, v in _HORARIO_DEFAULT.items():
                emp["horario"].setdefault(k, v)

        return activos

    # Fallback: empleado único desde .env
    load_dotenv()
    usuario = os.getenv("GEOVICTORIA_USER")
    password = os.getenv("GEOVICTORIA_PASSWORD")

    if not usuario or not password:
        raise ValueError(
            "Configure GEOVICTORIA_USER y GEOVICTORIA_PASSWORD en .env "
            "o cree config/employees.json. Vea config/employees.example.json como referencia."
        )

    return [
        {
            "id": "default",
            "nombre": usuario,
            "usuario": usuario,
            "password": password,
            "activo": True,
            "horario": dict(_HORARIO_DEFAULT),
        }
    ]
