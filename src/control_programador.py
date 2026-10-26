"""Iniciar, detener y reiniciar el programador desde el monitor (sin tocar archivos .bat).

Solo actúa sobre procesos de python cuya línea de comandos contiene programador.py: jamás toca otros
procesos. El programador nuevo se lanza sin consola propia y heredando el entorno del monitor, de modo
que el navegador sigue visible o headless según cómo se arrancó el monitor (GEOVICTORIA_HEADLESS).
"""
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

_SCRIPT = "programador.py"


def _es_programador(p) -> bool:
    try:
        nombre = (p.info.get("name") or "").lower()
        return nombre.startswith("python") and any(_SCRIPT in (parte or "") for parte in (p.info.get("cmdline") or []))
    except Exception:
        return False


def procesos_programador() -> List:
    """Procesos del programador (el lanzador del venv y su intérprete cuentan por separado)."""
    import psutil

    return [p for p in psutil.process_iter(["pid", "name", "cmdline"]) if _es_programador(p) and p.pid != os.getpid()]


def detener(espera_seg: float = 10.0) -> int:
    """Cierra el programador. Devuelve cuántos procesos terminó; lanza RuntimeError si alguno sigue vivo."""
    import psutil

    procesos = procesos_programador()
    for p in procesos:
        try:
            p.terminate()
        except psutil.Error:
            pass
    _, vivos = psutil.wait_procs(procesos, timeout=espera_seg)
    for p in vivos:
        try:
            p.kill()
        except psutil.Error:
            pass
    _, vivos = psutil.wait_procs(vivos, timeout=espera_seg)
    if vivos:
        raise RuntimeError(f"No se pudo cerrar el programador (PID {', '.join(str(p.pid) for p in vivos)})")
    return len(procesos)


def iniciar(raiz: Path, python: Optional[str] = None) -> int:
    """Lanza el programador desacoplado de este proceso y sin ventana. Devuelve el PID del lanzador."""
    opciones = {}
    if sys.platform == "win32":
        opciones["creationflags"] = (subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                                     | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        opciones["start_new_session"] = True
    proceso = subprocess.Popen(
        [python or sys.executable, str(Path("src") / _SCRIPT)], cwd=str(raiz),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **opciones,
    )
    return proceso.pid


def esperar_arranque(segundos: float = 15.0) -> bool:
    """True si aparece un programador en ejecución dentro del plazo."""
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if procesos_programador():
            return True
        time.sleep(0.5)
    return False
