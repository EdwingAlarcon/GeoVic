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


def _es_programador(p, incluir_ventanas: bool = False) -> bool:
    """Proceso python de programador.py; con `incluir_ventanas`, también la consola `cmd /k` que lo envuelve."""
    try:
        nombre = (p.info.get("name") or "").lower()
        es_candidato = nombre.startswith("python") or (incluir_ventanas and nombre in ("cmd", "cmd.exe"))
        return es_candidato and any(_SCRIPT in (parte or "") for parte in (p.info.get("cmdline") or []))
    except Exception:
        return False


def procesos_programador(incluir_ventanas: bool = False) -> List:
    """Procesos del programador (el lanzador del venv y su intérprete cuentan por separado).

    Por defecto solo procesos python: sirve para saber si el programador corre. Con `incluir_ventanas`
    añade las consolas `cmd /k` que lo envuelven, que quedan abiertas y vacías cuando el python muere.
    """
    import psutil

    return [p for p in psutil.process_iter(["pid", "name", "cmdline"])
            if _es_programador(p, incluir_ventanas) and p.pid != os.getpid()]


def detener(espera_seg: float = 10.0) -> int:
    """Cierra el programador y su ventana de consola. Devuelve cuántos procesos terminó; lanza RuntimeError
    si alguno sigue vivo. Cerrar también la consola evita que se acumulen ventanas vacías."""
    import psutil

    procesos = procesos_programador(incluir_ventanas=True)
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


def _lanzar(raiz: Path, argumentos: List[str], python: Optional[str] = None) -> int:
    """Lanza `python <argumentos>` desacoplado de este proceso y sin ventana. Devuelve el PID."""
    opciones = {}
    if sys.platform == "win32":
        opciones["creationflags"] = (subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                                     | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        opciones["start_new_session"] = True
    proceso = subprocess.Popen(
        [python or sys.executable, *argumentos], cwd=str(raiz),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **opciones,
    )
    return proceso.pid


def iniciar(raiz: Path, python: Optional[str] = None) -> int:
    """Lanza el programador desacoplado de este proceso. Devuelve el PID del lanzador.

    En Windows abre una ventana de consola visible ("Programador GeoVictoria", con `cmd /k` para poder ver
    el log), igual que actualizar_servidor.bat: así el navegador sigue visible en la sesión del usuario y
    no hay un programador "invisible" que nadie sepa dónde cerrar. En otros sistemas, sin ventana.
    """
    python = python or sys.executable
    if sys.platform == "win32":
        # Cadena completa (no lista): las comillas externas de `cmd /k ""python" script"` hacen falta si la
        # ruta de python tiene espacios, y list2cmdline no las genera.
        linea = f'cmd /c start "Programador GeoVictoria" /D "{raiz}" cmd /k ""{python}" {Path("src") / _SCRIPT}"'
        return subprocess.Popen(linea, cwd=str(raiz), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW).pid
    return _lanzar(raiz, [str(Path("src") / _SCRIPT)], python)


def lanzar_marcado(raiz: Path, pendientes: List[dict], python: Optional[str] = None) -> int:
    """Lanza scripts/marcar_pendientes.py para los pares {"id", "accion"} dados (en segundo plano)."""
    pares = [f"{p['id']}:{p['accion']}" for p in pendientes]
    return _lanzar(raiz, [str(Path("scripts") / "marcar_pendientes.py"), *pares], python)


def esperar_arranque(segundos: float = 15.0) -> bool:
    """True si aparece un programador en ejecución dentro del plazo."""
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if procesos_programador():
            return True
        time.sleep(0.5)
    return False
