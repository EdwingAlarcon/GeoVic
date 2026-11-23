"""
Carga y valida la configuración de empleados.
Soporta modo individual (.env) y multi-empleado (config/employees.json).
"""
import copy
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

from src import novedades

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


def _fecha_iso(valor) -> Optional[date]:
    try:
        return date.fromisoformat(str(valor))
    except (ValueError, TypeError):
        return None


def _rango_ausencia(ausencia) -> Optional[Tuple[date, Optional[date], str]]:
    """(desde, hasta, motivo) de una entrada de "ausencias", o None si está mal escrita.

    "hasta" es opcional (licencia sin fecha de fin: hasta = None); si se escribe debe ser una fecha
    válida y no anterior a "desde".
    """
    if not isinstance(ausencia, dict):
        return None
    desde = _fecha_iso(ausencia.get("desde"))
    if desde is None:
        return None
    hasta = None
    if ausencia.get("hasta"):
        hasta = _fecha_iso(ausencia["hasta"])
        if hasta is None or hasta < desde:
            return None
    return desde, hasta, str(ausencia.get("motivo") or "ausencia")


def ausencia_en(empleado: Dict, dia: date) -> Optional[str]:
    """Motivo si el empleado está exento de marcar ese día ("ausencias" en employees.json), o None.

    Las entradas mal escritas se ignoran (ver ausencias_invalidas): es preferible marcar de más a
    que un error de digitación deje a alguien sin marcar o impida arrancar el programador.
    """
    ausencias = empleado.get("ausencias")
    for ausencia in ausencias if isinstance(ausencias, list) else []:
        rango = _rango_ausencia(ausencia)
        if rango and rango[0] <= dia and (rango[1] is None or dia <= rango[1]):
            return rango[2]
    return None


def ausencias_invalidas(empleado: Dict) -> List[str]:
    """Entradas de "ausencias" que se ignoran por estar mal escritas (para avisar al arrancar)."""
    ausencias = empleado.get("ausencias")
    if ausencias is None:
        return []
    if not isinstance(ausencias, list):
        return [json.dumps(ausencias, ensure_ascii=False)]
    return [json.dumps(a, ensure_ascii=False) for a in ausencias if _rango_ausencia(a) is None]


# --- Reemplazos temporales ------------------------------------------------------
# Una persona que hoy no está en el sistema cubre por unos días el turno de otra. Se da de alta en
# employees.json (con SUS credenciales) y un bloque:
#     "reemplazo": {"cubre_a": "emp07", "desde": "2026-12-01", "hasta": "2026-12-05"}
# Dentro del periodo marca con el horario de quien cubre (salvo que tenga "horario" propio) y la persona
# cubierta queda ausente ("cubierto por …"). Fuera del periodo el reemplazo NO marca. Si el bloque está
# mal escrito, el reemplazo no marca nunca (es alguien nuevo: no marcar es más seguro que marcar mal) y
# la persona cubierta sigue marcando normal.

_ANTES_DE_TODO = "2000-01-01"
_ULTIMOS_TODOS: List[Dict] = []  # última lectura válida de employees.json (respaldo si no se puede releer)


def reemplazo_de(empleado: Dict, ids: Optional[List] = None) -> Optional[Dict]:
    """None si no es un reemplazo; {"cubre_a", "desde", "hasta"} si es válido; {"invalido": texto} si no."""
    r = empleado.get("reemplazo")
    if r is None:
        return None
    if not isinstance(r, dict):
        return {"invalido": "el bloque 'reemplazo' debe ser un objeto"}
    desde, hasta = _fecha_iso(r.get("desde")), _fecha_iso(r.get("hasta"))
    if not r.get("cubre_a"):
        return {"invalido": "falta 'cubre_a' (id de la persona a la que cubre)"}
    if ids is not None and r["cubre_a"] not in ids:
        return {"invalido": f"'cubre_a' = {r['cubre_a']} no existe en employees.json"}
    if r["cubre_a"] == empleado.get("id"):
        return {"invalido": "no puede cubrirse a sí mismo"}
    if desde is None or hasta is None:
        return {"invalido": "'desde' y 'hasta' son obligatorios (AAAA-MM-DD)"}
    if hasta < desde:
        return {"invalido": "'hasta' es anterior a 'desde'"}
    return {"cubre_a": r["cubre_a"], "desde": desde, "hasta": hasta}


def ultimos_empleados() -> List[Dict]:
    """Todos los empleados (activos o no) de la última lectura válida de employees.json."""
    return list(_ULTIMOS_TODOS)


def reemplazos_invalidos(todos: List[Dict]) -> List[Tuple[Dict, str]]:
    """(empleado, motivo) de cada bloque "reemplazo" mal escrito, para avisar al arrancar."""
    ids = [e.get("id") for e in todos]
    return [(e, r["invalido"]) for e in todos if (r := reemplazo_de(e, ids)) and "invalido" in r]


def ausencias_por_reemplazo(todos: List[Dict]) -> Dict[str, List[Dict]]:
    """Ausencias que se deducen de los reemplazos: el reemplazo fuera de su periodo y el cubierto dentro."""
    ids = [e.get("id") for e in todos]
    nombres = {e.get("id"): e.get("nombre") or e.get("id") for e in todos}
    extra: Dict[str, List[Dict]] = {}
    for e in todos:
        r = reemplazo_de(e, ids)
        if r is None:
            continue
        propias = extra.setdefault(e.get("id"), [])
        if "invalido" in r:
            propias.append({"desde": _ANTES_DE_TODO, "motivo": f"reemplazo mal configurado: {r['invalido']}"})
            continue
        if r["desde"] > date.fromisoformat(_ANTES_DE_TODO):
            propias.append({"desde": _ANTES_DE_TODO, "hasta": (r["desde"] - timedelta(days=1)).isoformat(),
                            "motivo": f"reemplazo: empieza el {r['desde'].isoformat()}"})
        propias.append({"desde": (r["hasta"] + timedelta(days=1)).isoformat(),
                        "motivo": f"reemplazo: terminó el {r['hasta'].isoformat()}"})
        extra.setdefault(r["cubre_a"], []).append(
            {"desde": r["desde"].isoformat(), "hasta": r["hasta"].isoformat(), "motivo": f"cubierto por {nombres[e.get('id')]}"})
    return extra


def resolver_reemplazos(todos: List[Dict]) -> List[Dict]:
    """Copias de los empleados con el horario de reemplazo aplicado y sus ausencias deducidas añadidas."""
    por_id = {e.get("id"): e for e in todos}
    ids = list(por_id)
    extra = ausencias_por_reemplazo(todos)
    salida = []
    for e in todos:
        copia = dict(e)
        r = reemplazo_de(e, ids)
        if r and "invalido" not in r and not e.get("horario"):
            copia["horario"] = copy.deepcopy(por_id[r["cubre_a"]].get("horario") or {})
        if extra.get(e.get("id")):
            propias = e.get("ausencias")
            propias = list(propias) if isinstance(propias, list) else ([] if propias is None else [propias])
            copia["ausencias"] = propias + extra[e.get("id")]
        salida.append(copia)
    return salida


def ruta_novedades() -> Path:
    """config/novedades.json (lo escribe el monitor). Se calcula en cada uso, junto a EMPLOYEES_FILE."""
    return novedades.ruta_novedades(EMPLOYEES_FILE)


def ausencia_vigente(empleado: Dict, dia: date) -> Optional[str]:
    """Como ausencia_en, pero relee employees.json y novedades.json: añadir unas vacaciones (a mano o
    desde el monitor) no exige reiniciar el programador. Si employees.json no se puede leer se usa lo
    cargado al arrancar; si novedades.json está ilegible, su última lectura válida."""
    emp_id = empleado.get("id")
    leidos: Optional[List[Dict]] = None
    try:
        with open(EMPLOYEES_FILE, "r", encoding="utf-8") as f:
            crudo = json.load(f).get("employees", [])
        if isinstance(crudo, list):
            leidos = [e for e in crudo if isinstance(e, dict)]
            _ULTIMOS_TODOS[:] = leidos
    except (OSError, ValueError, AttributeError):
        pass
    # Sin lectura válida: los datos propios son los cargados al arrancar y los reemplazos se deducen de
    # la última lista buena. Los reemplazos se resuelven con la lista completa: el cubierto no sabe por
    # sí solo que lo cubren.
    fuente = leidos if leidos is not None else list(_ULTIMOS_TODOS)
    propio = next((e for e in leidos or [] if e.get("id") == emp_id), empleado)
    lista_completa = [propio if e.get("id") == emp_id else e for e in fuente]
    if not any(e.get("id") == emp_id for e in fuente):
        lista_completa.append(propio)
    actual = next(e for e in resolver_reemplazos(lista_completa) if e.get("id") == emp_id)
    lista, _ = novedades.leer(ruta_novedades())
    return ausencia_en(novedades.combinar(actual, lista), dia)


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

        todos = [e for e in data.get("employees", []) if isinstance(e, dict)]
        _ULTIMOS_TODOS[:] = todos
        # Reemplazos: horario de quien cubren (se resuelve con todos, aunque el cubierto esté inactivo)
        activos = [e for e in resolver_reemplazos(todos) if e.get("activo", True)]

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
