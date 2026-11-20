"""Logs de texto con un archivo por día y SIN renombrar nunca un archivo.

Por qué no RotatingFileHandler: rota renombrando el archivo, y en Windows no se puede renombrar un
archivo que otro tenga abierto (el stderr redirigido del propio programador, el monitor leyendo el
log, ver_log_en_vivo.bat, otro proceso escribiendo…). En producción, al llegar a 5 MB (~3 días) cada
línea de log intentaba rotar, fallaba con WinError 32 y en su lugar se volcaba un traceback: 440 MB
de logs, el texto útil enterrado sin hora ni nivel, y el panel "Log en vivo" lleno de errores.

Aquí cada día tiene su archivo (<prefijo>_AAAAMMDD.log). Al cambiar de fecha se cierra el actual y
se abre el del día nuevo; nada se renombra, así que ningún lector puede bloquearlo. El volumen real
es ~1,8 MB/día (medido en el servidor), por eso no hay tope de tamaño. La limpieza de logs viejos
se ejecuta también al cambiar de día, no solo al arrancar (el programador vive semanas).
"""
import logging
import os
import threading
from datetime import date
from pathlib import Path
from typing import Callable, Optional


def ruta_del_dia(carpeta: Path, prefijo: str, fecha: date) -> Path:
    return Path(carpeta) / f"{prefijo}_{fecha:%Y%m%d}.log"


class ArchivoDiario(logging.FileHandler):
    """FileHandler que escribe en el archivo de la fecha actual y cambia de archivo a medianoche."""

    def __init__(self, carpeta: Path, prefijo: str, al_cambiar_dia: Optional[Callable[[], None]] = None,
                 hoy: Callable[[], date] = date.today):
        self.carpeta, self.prefijo = Path(carpeta), prefijo
        self._hoy, self._al_cambiar_dia = hoy, al_cambiar_dia
        self.fecha = hoy()
        self.carpeta.mkdir(parents=True, exist_ok=True)
        super().__init__(ruta_del_dia(self.carpeta, prefijo, self.fecha), mode="a", encoding="utf-8")

    def emit(self, record: logging.LogRecord) -> None:
        # handle() ya tiene el candado del handler: el cambio de archivo no se cruza con otra escritura
        hoy = self._hoy()
        if hoy != self.fecha:
            self._cambiar_a(hoy)
        super().emit(record)

    def _cambiar_a(self, fecha: date) -> None:
        self.fecha = fecha
        if self.stream:
            self.stream.close()
            self.stream = None
        self.baseFilename = os.path.abspath(ruta_del_dia(self.carpeta, self.prefijo, fecha))
        self.stream = self._open()
        if self._al_cambiar_dia:
            try:
                self._al_cambiar_dia()
            except Exception:
                pass  # limpiar logs nunca debe impedir escribir el log


class StderrDiario:
    """Sustituto de sys.stderr: escribe en <prefijo>_AAAAMMDD.log del día, abriendo y cerrando en cada
    escritura (no deja el archivo abierto, así que tampoco puede bloquear a nadie).

    Va a un archivo propio y no al logging a propósito: logging informa de sus propios fallos por
    sys.stderr, y si sys.stderr volviera al logging un fallo se repetiría sin fin.
    """

    encoding = "utf-8"
    errors = "replace"

    def __init__(self, carpeta: Path, prefijo: str, hoy: Callable[[], date] = date.today):
        self.carpeta, self.prefijo, self._hoy = Path(carpeta), prefijo, hoy
        self._candado = threading.Lock()

    @property
    def ruta(self) -> Path:
        return ruta_del_dia(self.carpeta, self.prefijo, self._hoy())

    def write(self, texto: str) -> int:
        try:
            with self._candado, open(self.ruta, "a", encoding="utf-8", errors="replace") as f:
                f.write(texto)
        except Exception:
            pass  # stderr no tiene a quién avisar
        return len(texto)

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False
