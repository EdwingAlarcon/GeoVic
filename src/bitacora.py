"""Bitácora de eventos y latido del programador.

El log de texto mezcla procesos, rota y puede perder líneas (en producción se vio un hueco de 38
minutos). Aquí cada evento es una línea JSON en src/logs/eventos_AAAAMMDD.jsonl, escrita y
sincronizada al instante, que el monitor y los diagnósticos leen sin interpretar texto.

Registrar un evento NUNCA debe romper un marcaje: todos los errores se tragan. Nada de lo que se
guarda incluye usuarios ni contraseñas: solo id y nombre del empleado.
"""
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

LOG_DIR = Path(__file__).parent / "logs"

_candado = threading.Lock()


def _ruta_eventos(fecha: Optional[str] = None) -> Path:
    fecha = fecha or datetime.now().strftime("%Y%m%d")
    return LOG_DIR / f"eventos_{fecha}.jsonl"


def _ruta_latido() -> Path:
    return LOG_DIR / "latido.json"


def registrar(tipo: str, empleado: Optional[Dict] = None, **datos) -> None:
    """Agrega un evento a la bitácora de hoy. Nunca lanza excepciones."""
    try:
        evento = {"ts": datetime.now().isoformat(timespec="seconds"), "pid": os.getpid(), "tipo": tipo}
        if empleado:
            evento["emp_id"] = empleado.get("id")
            evento["nombre"] = empleado.get("nombre")
        evento.update(datos)
        linea = json.dumps(evento, ensure_ascii=False, default=str) + "\n"
        with _candado:
            LOG_DIR.mkdir(exist_ok=True)
            with open(_ruta_eventos(), "a", encoding="utf-8") as f:
                f.write(linea)
                f.flush()
                os.fsync(f.fileno())
    except Exception:
        pass


def leer_eventos(fecha: Optional[str] = None) -> List[Dict]:
    """Eventos de un día (por defecto hoy), en orden. Ignora líneas truncadas por un corte."""
    ruta = _ruta_eventos(fecha)
    eventos: List[Dict] = []
    try:
        if not ruta.exists():
            return eventos
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            for linea in f:
                try:
                    eventos.append(json.loads(linea))
                except ValueError:
                    continue
    except OSError:
        pass
    return eventos


def escribir_latido(inicio: str, fase: str, plan: Dict, tick_scheduler: Optional[str] = None) -> None:
    """Sobrescribe (de forma atómica) el archivo de latido. Nunca lanza excepciones.

    fase: "arrancando" mientras revisa pendientes, "activo" cuando el scheduler ya corre.
    tick_scheduler: última vez que un job del scheduler se ejecutó (prueba de que el scheduler responde).
    """
    try:
        datos = {
            "pid": os.getpid(),
            "inicio": inicio,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "fase": fase,
            "tick_scheduler": tick_scheduler,
            "plan": plan,
        }
        destino = _ruta_latido()
        LOG_DIR.mkdir(exist_ok=True)
        temporal = destino.with_suffix(".tmp")
        temporal.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        os.replace(temporal, destino)
    except Exception:
        pass


def leer_latido() -> Optional[Dict]:
    try:
        return json.loads(_ruta_latido().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
