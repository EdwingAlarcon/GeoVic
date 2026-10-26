"""Decide cuándo se puede reintentar un marcaje que el portal no registró.

Lógica pura (sin I/O) para poder probarla con casos controlados. La regla de seguridad contra
duplicados no vive aquí sino en geovictoria.run(): solo hace clic si el portal ofrece el botón
esperado, y un botón ofrecido significa que ese marcaje NO está registrado. Aquí solo se acota
cuántas veces y hasta qué hora se insiste.
"""
import os
from datetime import datetime, time, timedelta
from typing import Tuple

MAX_TARDE_MIN = 120      # no se reintenta pasadas 2 h de la hora programada
ANTES_MIN = 30           # ni antes de la ventana de marcaje (±30 min) de la hora programada
REINTENTOS_DEFECTO = 2
DEMORA_DEFECTO_SEG = 180


def reintentos_desde_entorno(defecto: int = REINTENTOS_DEFECTO) -> int:
    """GEOVICTORIA_REINTENTOS: máximo de reintentos por marcaje (0 los desactiva)."""
    try:
        return max(0, int(os.getenv("GEOVICTORIA_REINTENTOS", defecto)))
    except ValueError:
        return defecto


def demora_reintento_desde_entorno(defecto: int = DEMORA_DEFECTO_SEG) -> int:
    """GEOVICTORIA_REINTENTO_DEMORA: segundos de espera antes de cada reintento."""
    try:
        return max(1, int(os.getenv("GEOVICTORIA_REINTENTO_DEMORA", defecto)))
    except ValueError:
        return defecto


def puede_reintentar(ahora: datetime, hora_programada: time, reintento: int, max_reintentos: int,
                     max_tarde_min: int = MAX_TARDE_MIN) -> Tuple[bool, str]:
    """(se puede, motivo si no). `reintento` es el número del reintento que se quiere hacer (1, 2…)."""
    if max_reintentos <= 0:
        return False, "los reintentos están desactivados"
    if reintento > max_reintentos:
        return False, f"se agotaron los {max_reintentos} reintentos"
    programada = datetime.combine(ahora.date(), hora_programada)
    if ahora < programada - timedelta(minutes=ANTES_MIN):
        return False, "todavía no es la hora de este marcaje"
    if ahora > programada + timedelta(minutes=max_tarde_min):
        return False, f"pasaron más de {max_tarde_min} min de su hora programada"
    return True, ""
