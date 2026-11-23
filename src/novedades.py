"""Novedades del personal (vacaciones, licencias, desactivar, retiro) gestionadas desde el monitor.

Se guardan en config/novedades.json, junto a employees.json pero SIN credenciales: el monitor escribe
solo aquí y nunca toca el archivo de usuarios y contraseñas. Cada novedad es una ausencia con id:

    {"novedades": [{"id": "n1a2b3c4", "emp_id": "e1", "tipo": "ausencia" | "desactivado" | "retiro",
                    "desde": "2026-12-20", "hasta": "2027-01-10" | null, "motivo": "vacaciones",
                    "creada": "2026-11-23T10:00:00"}]}

Se combinan con las "ausencias" escritas a mano en employees.json (empleados.ausencia_vigente y el
monitor) y valen sin reiniciar el programador, porque se releen en cada comprobación.

Lectura: un archivo que no existe = sin novedades. Un archivo que existe pero no se puede leer NO se
toma como "sin novedades" (marcaría a gente de vacaciones: un registro de asistencia falso): se usa la
última lectura buena y se avisa.
"""
import json
import secrets
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

NOMBRE_ARCHIVO = "novedades.json"
TIPOS = ("ausencia", "desactivado", "retiro")
MOTIVO_MAX = 60
DIAS_FUTURO_MAX = 400  # una fecha más lejana es casi seguro un error de digitación (2062 por 2026)

_ULTIMO_BUENO: Dict[str, List[Dict]] = {}
_candado_escritura = threading.Lock()


class NovedadInvalida(ValueError):
    """Datos rechazados al guardar: el mensaje se muestra tal cual en el monitor."""


def ruta_novedades(ruta_empleados: Path) -> Path:
    """novedades.json vive junto a employees.json (así los tests con un employees.json temporal quedan aislados)."""
    return Path(ruta_empleados).parent / NOMBRE_ARCHIVO


def leer(ruta: Path) -> Tuple[List[Dict], Optional[str]]:
    """(novedades, error). Nunca lanza.

    Sin archivo -> ([], None). Ilegible -> (última lectura buena o [], mensaje de error).
    """
    clave = str(Path(ruta).resolve())
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        lista = datos.get("novedades") if isinstance(datos, dict) else None
        if not isinstance(lista, list):
            raise ValueError("falta la lista 'novedades'")
    except FileNotFoundError:
        _ULTIMO_BUENO[clave] = []
        return [], None
    except (OSError, ValueError) as e:
        return list(_ULTIMO_BUENO.get(clave, [])), f"{Path(ruta).name} ilegible ({e}): se usa la última lectura válida"
    lista = [n for n in lista if isinstance(n, dict)]
    _ULTIMO_BUENO[clave] = lista
    return list(lista), None


def como_ausencias(novedades: List[Dict], emp_id) -> List[Dict]:
    """Las novedades de un empleado en el formato de "ausencias" de employees.json."""
    return [{"desde": n.get("desde"), "hasta": n.get("hasta"), "motivo": n.get("motivo") or n.get("tipo")}
            for n in novedades if n.get("emp_id") == emp_id]


def combinar(empleado: Dict, novedades: List[Dict]) -> Dict:
    """Copia del empleado con sus novedades añadidas a "ausencias" (las de employees.json se conservan)."""
    propias = empleado.get("ausencias")
    propias = list(propias) if isinstance(propias, list) else ([] if propias is None else [propias])
    return {**empleado, "ausencias": propias + como_ausencias(novedades, empleado.get("id"))}


def vigentes_o_futuras(novedades: List[Dict], emp_id, hoy: date) -> List[Dict]:
    """Novedades del empleado que aún no han terminado (para listarlas en el monitor), por fecha."""
    salida = []
    for n in novedades:
        if n.get("emp_id") != emp_id:
            continue
        hasta = _fecha(n.get("hasta"))
        if n.get("hasta") and hasta is not None and hasta < hoy:
            continue
        salida.append({k: n.get(k) for k in ("id", "tipo", "desde", "hasta", "motivo")})
    return sorted(salida, key=lambda n: str(n.get("desde")))


# --- Validación y escritura ----------------------------------------------------

def _fecha(valor) -> Optional[date]:
    try:
        return date.fromisoformat(str(valor))
    except (ValueError, TypeError):
        return None


def _fecha_obligatoria(valor, campo: str) -> date:
    f = _fecha(valor)
    if f is None:
        raise NovedadInvalida(f"Fecha '{campo}' no válida: usa el formato AAAA-MM-DD.")
    return f


def construir(datos: Dict, ids_empleados: List, hoy: date) -> Dict:
    """Valida lo que llega del monitor y devuelve la novedad lista para guardar.

    datos: {"emp_id", "tipo": "ausencia"|"desactivado"|"retiro", "desde", "hasta", "motivo", "ultimo_dia"}
      - ausencia: desde (obligatorio), hasta (opcional), motivo.
      - desactivado: desde hoy, sin fin (se quita con "Reactivar").
      - retiro: ultimo_dia = último día que marca; deja de marcar desde el día siguiente.
    """
    emp_id = datos.get("emp_id")
    if emp_id not in ids_empleados:
        raise NovedadInvalida("Empleado desconocido.")
    tipo = datos.get("tipo")
    if tipo not in TIPOS:
        raise NovedadInvalida("Tipo de novedad desconocido.")
    motivo = " ".join(str(datos.get("motivo") or "").split())[:MOTIVO_MAX]
    limite = hoy + timedelta(days=DIAS_FUTURO_MAX)

    if tipo == "desactivado":
        desde, hasta, motivo = hoy, None, motivo or "desactivado"
    elif tipo == "retiro":
        ultimo = _fecha_obligatoria(datos.get("ultimo_dia"), "último día")
        if ultimo < hoy - timedelta(days=1):
            raise NovedadInvalida("El último día no puede ser anterior a ayer.")
        desde, hasta, motivo = ultimo + timedelta(days=1), None, motivo or "retiro"
    else:
        desde = _fecha_obligatoria(datos.get("desde"), "desde")
        hasta = _fecha_obligatoria(datos.get("hasta"), "hasta") if datos.get("hasta") else None
        if hasta is not None and hasta < desde:
            raise NovedadInvalida("'Hasta' no puede ser anterior a 'desde'.")
        if hasta is not None and hasta < hoy:  # sin "hasta" no termina (p. ej. incapacidad que se registra tarde)
            raise NovedadInvalida("Esa ausencia ya terminó: revisa las fechas.")
        motivo = motivo or "ausencia"
    if desde > limite:
        raise NovedadInvalida(f"La fecha {desde.isoformat()} está a más de {DIAS_FUTURO_MAX} días: revisa el año.")
    if hasta is not None and hasta > limite:
        raise NovedadInvalida(f"La fecha {hasta.isoformat()} está a más de {DIAS_FUTURO_MAX} días: revisa el año.")

    return {"id": "n" + secrets.token_hex(4), "emp_id": emp_id, "tipo": tipo,
            "desde": desde.isoformat(), "hasta": hasta.isoformat() if hasta else None,
            "motivo": motivo, "creada": datetime.now().isoformat(timespec="seconds")}


def se_solapa(nueva: Dict, existentes: List[Dict]) -> Optional[Dict]:
    """Primera novedad del mismo empleado cuyo rango se cruza con la nueva, o None."""
    d1, h1 = _fecha(nueva["desde"]), _fecha(nueva.get("hasta")) or date.max
    for n in existentes:
        if n.get("emp_id") != nueva["emp_id"]:
            continue
        d2 = _fecha(n.get("desde"))
        h2 = _fecha(n.get("hasta")) if n.get("hasta") else date.max
        if d2 is None or h2 is None:
            continue
        if d1 <= h2 and d2 <= h1:
            return n
    return None


def afecta_hoy(novedad: Dict, hoy: date) -> bool:
    d, h = _fecha(novedad.get("desde")), _fecha(novedad.get("hasta")) if novedad.get("hasta") else date.max
    return d is not None and h is not None and d <= hoy <= h


def _escribir(ruta: Path, novedades: List[Dict]) -> None:
    from src.bitacora import escribir_json_atomico
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    escribir_json_atomico(Path(ruta), {"novedades": novedades})
    _ULTIMO_BUENO[str(Path(ruta).resolve())] = list(novedades)


def agregar(ruta: Path, nueva: Dict) -> Dict:
    """Guarda una novedad ya validada (ver construir). Lanza NovedadInvalida si se solapa con otra."""
    with _candado_escritura:
        actuales, error = leer(ruta)
        if error:
            raise NovedadInvalida(f"No se guarda nada: {error}. Corrige o borra el archivo primero.")
        choque = se_solapa(nueva, actuales)
        if choque:
            fin = choque.get("hasta") or "sin fecha de fin"
            raise NovedadInvalida(f"Se cruza con otra novedad del mismo empleado ({choque.get('motivo')}: "
                                  f"{choque.get('desde')} → {fin}). Quita esa primero.")
        _escribir(ruta, actuales + [nueva])
    return nueva


def terminar(ruta: Path, novedad_id: str, hoy: date) -> Tuple[Dict, str]:
    """Quita o cierra una novedad. Devuelve (novedad original, "eliminada" | "cerrada").

    Si aún no ha empezado o empezó hoy, se elimina (cerrarla en "ayer" dejaría hasta < desde, un rango
    inválido). Si ya estaba en curso, se cierra con hasta = ayer: el historial se conserva y hoy vuelve
    a marcar.
    """
    with _candado_escritura:
        actuales, error = leer(ruta)
        if error:
            raise NovedadInvalida(f"No se modifica nada: {error}.")
        objetivo = next((n for n in actuales if n.get("id") == novedad_id), None)
        if objetivo is None:
            raise NovedadInvalida("Esa novedad ya no existe (¿se quitó en otra pestaña?).")
        desde = _fecha(objetivo.get("desde"))
        ayer = hoy - timedelta(days=1)
        if desde is None or desde >= hoy:
            resto, como = [n for n in actuales if n is not objetivo], "eliminada"
        else:
            hasta = _fecha(objetivo.get("hasta")) if objetivo.get("hasta") else None
            if hasta is not None and hasta < hoy:
                raise NovedadInvalida("Esa novedad ya había terminado.")
            resto = [({**n, "hasta": ayer.isoformat()} if n is objetivo else n) for n in actuales]
            como = "cerrada"
        _escribir(ruta, resto)
    return objetivo, como
