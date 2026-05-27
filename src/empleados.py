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
    # "dias": {}  # overrides por día — clave opcional, ver employees.example.json
}

# Mapeo nombre de día en config → weekday de Python (0=lunes, 5=sábado)
_NOMBRE_DIA_A_WEEKDAY: Dict[str, int] = {
    "lun": 0, "mar": 1, "mie": 2, "jue": 3, "vie": 4, "sab": 5,
}


def obtener_horario_dia(horario: Dict, dia_semana: int) -> Dict:
    """
    Retorna el horario efectivo de entrada/salida para el día indicado.

    Parámetros:
        horario    — dict del empleado (con claves estándar + opcional "dias")
        dia_semana — int de Python: 0=lunes … 5=sábado, 6=domingo

    Retorna un dict con:
        entrada_hora, entrada_minuto, salida_hora, salida_minuto

    Si existe una clave en horario["dias"] para ese día, sus valores sobreescriben
    el horario base de semana/sábado.  Cualquier subclave faltante se toma del base.
    """
    if dia_semana == 5:
        base = {
            "entrada_hora":   horario["entrada_sabado_hora"],
            "entrada_minuto": horario["entrada_sabado_minuto"],
            "salida_hora":    horario["salida_sabado_hora"],
            "salida_minuto":  horario["salida_sabado_minuto"],
        }
    else:
        base = {
            "entrada_hora":   horario["entrada_semana_hora"],
            "entrada_minuto": horario["entrada_semana_minuto"],
            "salida_hora":    horario["salida_semana_hora"],
            "salida_minuto":  horario["salida_semana_minuto"],
        }

    # Aplicar override específico del día si existe
    dias_override = horario.get("dias", {})
    for nombre_dia, idx in _NOMBRE_DIA_A_WEEKDAY.items():
        if idx == dia_semana and nombre_dia in dias_override:
            ov = dias_override[nombre_dia]
            base["entrada_hora"]   = ov.get("entrada_hora",   base["entrada_hora"])
            base["entrada_minuto"] = ov.get("entrada_minuto", base["entrada_minuto"])
            base["salida_hora"]    = ov.get("salida_hora",    base["salida_hora"])
            base["salida_minuto"]  = ov.get("salida_minuto",  base["salida_minuto"])
            break

    return base


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
