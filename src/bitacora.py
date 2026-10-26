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


def escribir_json_atomico(ruta: Path, datos, reintentos: int = 10) -> None:
    """Escribe `datos` como JSON sin dejar nunca el archivo a medias.

    Escribe en un temporal y lo reemplaza de golpe: un corte a mitad de escritura no deja el destino
    truncado (un registro truncado se lee como "sin marcajes" y podría repetir un marcaje). En Windows
    el reemplazo falla si otro proceso (p. ej. el monitor) tiene el destino abierto justo en ese
    instante, así que se reintenta unas décimas de segundo antes de rendirse.
    """
    temporal = ruta.with_suffix(".tmp")
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    espera = threading.Event()
    for intento in range(reintentos):
        try:
            os.replace(temporal, ruta)
            return
        except PermissionError:
            if intento == reintentos - 1:
                raise
            espera.wait(0.1)


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
        LOG_DIR.mkdir(exist_ok=True)
        escribir_json_atomico(_ruta_latido(), datos, reintentos=3)
    except Exception:
        pass


def leer_latido() -> Optional[Dict]:
    try:
        return json.loads(_ruta_latido().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
