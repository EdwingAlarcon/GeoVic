"""Control de concurrencia: una sola instancia del programador y tope de navegadores simultáneos.

Instancia única: el lock file con PID no basta. Los scripts de reinicio lo borran sin comprobar
que el proceso anterior murió, y entonces conviven varios programadores marcando a los mismos
empleados (en producción llegaron a ser tres a la vez). Aquí la exclusión la da el sistema
operativo (mutex con nombre en Windows, flock en POSIX): no se puede saltar borrando archivos y
se libera sola cuando el proceso muere, incluso con un kill o un reinicio del servidor.

Cupo de navegadores: cada job abre su propio Chromium. Si coinciden muchos (08:00, 18:00) el
equipo se satura y el login hace timeout; el cupo hace esperar a los demás en vez de fallar.
"""
import contextlib
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# "Global\" abarca todas las sesiones de Windows (RDP incluido), no solo la actual.
NOMBRE_MUTEX = "Global\\GeoVictoriaProgramadorUnico"

_ERROR_ACCESS_DENIED = 5
_ERROR_ALREADY_EXISTS = 183

_recurso_instancia = None  # handle/fd que mantiene la exclusión mientras viva el proceso


class InstanciaYaEnEjecucion(RuntimeError):
    """Otro programador ya tiene la exclusión de instancia única."""


def adquirir_instancia_unica(guard_path: Optional[Path] = None, nombre_mutex: str = NOMBRE_MUTEX) -> None:
    """Toma la exclusión de instancia única hasta que el proceso termine.

    Lanza InstanciaYaEnEjecucion si otro proceso ya la tiene. `guard_path` solo se usa fuera
    de Windows (archivo que se bloquea con flock; no debe borrarse).
    """
    global _recurso_instancia
    if sys.platform == "win32":
        _recurso_instancia = _adquirir_mutex_windows(nombre_mutex)
    else:
        if guard_path is None:
            raise ValueError("guard_path es obligatorio fuera de Windows")
        _recurso_instancia = _adquirir_flock(guard_path)


def _adquirir_mutex_windows(nombre: str):
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

    handle = kernel32.CreateMutexW(None, False, nombre)
    error = ctypes.get_last_error()

    if not handle:
        if error == _ERROR_ACCESS_DENIED:
            # El mutex existe y pertenece a otro usuario/sesión sin permisos para nosotros
            raise InstanciaYaEnEjecucion(nombre)
        raise OSError(error, f"No se pudo crear el mutex de instancia única '{nombre}'")
    if error == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        raise InstanciaYaEnEjecucion(nombre)
    return handle


def _adquirir_flock(guard_path: Path):
    import fcntl

    guard_path.parent.mkdir(parents=True, exist_ok=True)
    archivo = open(guard_path, "a+")
    try:
        fcntl.flock(archivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        archivo.close()
        raise InstanciaYaEnEjecucion(str(guard_path))
    return archivo


def maximo_navegadores_desde_entorno(defecto: int = 3) -> int:
    """Lee GEOVICTORIA_MAX_NAVEGADORES; un valor ausente o inválido usa el defecto."""
    try:
        return max(1, int(os.getenv("GEOVICTORIA_MAX_NAVEGADORES", defecto)))
    except ValueError:
        return defecto


class CupoNavegador:
    """Limita cuántos navegadores corren a la vez dentro del proceso."""

    def __init__(self, maximo: int):
        self.maximo = max(1, maximo)
        self._semaforo = threading.BoundedSemaphore(self.maximo)

    @contextlib.asynccontextmanager
    async def reservar(self, tag: str = ""):
        # Bloquea el hilo en vez de esperar con await: cada job corre su propio asyncio.run en
        # su propio hilo, así que solo se detiene ese job. Un acquire en executor podría
        # perder el cupo si la corrutina se cancela mientras espera.
        if not self._semaforo.acquire(blocking=False):
            logger.info(f"{tag}⏳ Esperando cupo de navegador (máx. {self.maximo} simultáneos)...")
            self._semaforo.acquire()
        try:
            yield
        finally:
            self._semaforo.release()
