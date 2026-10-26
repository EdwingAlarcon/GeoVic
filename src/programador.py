"""
Programador automático de marcaje de asistencia GeoVictoria.
Soporta múltiples empleados con horarios independientes.
"""
import asyncio
import atexit
import json
import logging
import os
import sys
import threading
from datetime import date, datetime, time, timedelta
from functools import partial
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import bitacora
from src.cache_estado import get_cache
from src.control_concurrencia import InstanciaYaEnEjecucion, adquirir_instancia_unica, desactivar_seleccion_consola
from src.empleados import cargar_empleados, obtener_horario_dia
from src.estado_monitor import confirmacion_de, marcajes_sin_confirmar
from src.festivos_colombia import es_festivo, listar_festivos_año
from src.geovictoria import run, verificar_estado
from src.reintentos import demora_reintento_desde_entorno, puede_reintentar, reintentos_desde_entorno

# ---------------------------------------------------------------------------
# Paths de archivos de estado
# ---------------------------------------------------------------------------

log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
lock_file = log_dir / "programador.lock"  # PID del programador activo (informativo)
guard_file = log_dir / "programador.guard"  # solo POSIX: archivo bloqueado con flock; no borrar
alerta_file = log_dir / "alertas.log"

# ---------------------------------------------------------------------------
# Logging con rotación (5 MB x 5 archivos)
# ---------------------------------------------------------------------------

log_file = log_dir / f"programador_{datetime.now().strftime('%Y%m%d')}.log"

_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
_fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8", mode="a")
_fh.setFormatter(_fmt)
# Forzar UTF-8 en la consola para que los emojis no rompan en Windows (cp1252)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_fh, _sh], force=True)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("📝 Sistema de logging inicializado")
logger.info(f"📁 Log: {log_file}")
logger.info("=" * 80)


def _limpiar_logs_viejos(dias: int = 14) -> None:
    """Borra archivos .log del directorio de logs con más de `dias` días de antigüedad.
    Excluye alertas.log (archivo de monitoreo externo, crece de forma acumulativa).
    """
    umbral = datetime.now().timestamp() - dias * 86400
    borrados = 0
    for archivo in log_dir.glob("*.log"):
        if archivo.name == "alertas.log":
            continue
        if archivo.stat().st_mtime < umbral:
            try:
                archivo.unlink()
                borrados += 1
            except OSError as e:
                logger.warning(f"No se pudo borrar {archivo.name}: {e}")
    if borrados:
        logger.info(f"🧹 Limpieza de logs: {borrados} archivo(s) eliminado(s) (>{dias} días)")


_limpiar_logs_viejos(dias=14)


# ---------------------------------------------------------------------------
# Configuración global de horarios (valores por defecto)
# ---------------------------------------------------------------------------

class HorarioConfig:
    COOLDOWN_ENTRE_MARCAJES = 300  # segundos
    STAGGER_SEGUNDOS = 10         # separación entre empleados con el mismo horario


def _aplicar_offset(hora: int, minuto: int, offset_segundos: int):
    """Convierte hora:minuto + offset en (hora, minuto, segundo) sin desbordamiento."""
    total = hora * 3600 + minuto * 60 + offset_segundos
    return total // 3600, (total % 3600) // 60, total % 60


# ---------------------------------------------------------------------------
# Estado compartido con el monitor (latido, plan horario) y confirmaciones
# ---------------------------------------------------------------------------

# Confirmación independiente: tras cada marcaje exitoso se vuelve a entrar al portal para comprobar
# que el botón de esa acción ya no se ofrece. GEOVICTORIA_CONFIRMAR=0 la desactiva.
CONFIRMAR = os.getenv("GEOVICTORIA_CONFIRMAR", "1").strip().lower() not in ("0", "false", "no")
CONFIRMAR_DEMORA_SEG = int(os.getenv("GEOVICTORIA_CONFIRMAR_DEMORA", "90"))

# Reintento de marcajes que el portal no registró: solo si un login nuevo comprueba que el portal SIGUE
# ofreciendo el botón (así no puede duplicar). GEOVICTORIA_REINTENTOS=0 lo desactiva.
REINTENTOS_MAX = reintentos_desde_entorno()
REINTENTO_DEMORA_SEG = demora_reintento_desde_entorno()

_scheduler: Optional[BlockingScheduler] = None  # lo fija main(); permite programar confirmaciones
_cola_confirmaciones: list = []                 # confirmaciones pedidas antes de que exista el scheduler
_cola_reintentos: list = []                     # reintentos pedidos antes de que exista el scheduler
_PLAN: Dict = {}      # hora programada real (con escalonado) de cada empleado y día, para el monitor
_NOMBRES: Dict = {}   # id -> nombre, para anotar eventos que solo conocen el id
_INICIO = datetime.now().isoformat(timespec="seconds")
_FASE = "arrancando"  # "activo" cuando el scheduler ya corre
_ULTIMO_TICK: Optional[str] = None


# ---------------------------------------------------------------------------
# Registro de ejecuciones — uno por empleado
# ---------------------------------------------------------------------------

def _registro_path(emp_id: str) -> Path:
    """Retorna la ruta al registro JSON de un empleado (backwards-compat para 'default')."""
    if emp_id == "default":
        return log_dir / "registro_ejecuciones.json"
    return log_dir / f"registro_{emp_id}.json"


def leer_registro(emp_id: str) -> dict:
    path = _registro_path(emp_id)
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except ValueError as e:  # JSON ilegible (p. ej. truncado por un corte): se conserva como evidencia
        logger.error(f"[{emp_id}] Registro ilegible ({e}): se guarda como .corrupto y se empieza uno nuevo")
        try:
            path.replace(path.with_name(f"{path.stem}.corrupto_{datetime.now():%Y%m%d_%H%M%S}.json"))
        except OSError:
            pass
    except Exception as e:
        logger.warning(f"[{emp_id}] Error leyendo registro: {e}")
    return {}


def guardar_registro(emp_id: str, tipo_marcaje: str, variacion_minutos: int = 0, origen: str = "programador") -> None:
    """Guarda el marcaje de hoy. origen: "programador" (hizo el clic) o "portal" (se detectó ya hecho)."""
    try:
        registro = leer_registro(emp_id)
        hoy = date.today().isoformat()
        ahora = datetime.now()

        registro.setdefault(hoy, {})[tipo_marcaje] = {
            "ejecutado": True,
            "hora": ahora.isoformat(),
            "timestamp": ahora.timestamp(),
            "variacion_minutos": variacion_minutos,
            "origen": origen,
        }

        # Mantener solo los últimos 30 días
        for fecha in sorted(registro.keys(), reverse=True)[30:]:
            del registro[fecha]

        bitacora.escribir_json_atomico(_registro_path(emp_id), registro)

        bitacora.registrar("registro", {"id": emp_id, "nombre": _NOMBRES.get(emp_id)},
                           tipo_marcaje=tipo_marcaje, origen=origen)

    except Exception as e:
        logger.error(f"[{emp_id}] Error guardando registro: {e}")


def ya_se_ejecuto_hoy(emp_id: str, tipo_marcaje: str) -> bool:
    registro = leer_registro(emp_id)
    hoy = date.today().isoformat()
    return registro.get(hoy, {}).get(tipo_marcaje, {}).get("ejecutado", False)


def anular_registro(emp_id: str, tipo_marcaje: str, motivo: str) -> None:
    """Marca como NO ejecutado un marcaje de hoy que el portal contradice.

    Un registro falso ("hecho") bloquea todo reintento y engaña al monitor. La marca original se
    conserva con `anulado` y `anulado_en` como evidencia, pero deja de contar como ejecutada.
    """
    try:
        registro = leer_registro(emp_id)
        marca = registro.get(date.today().isoformat(), {}).get(tipo_marcaje)
        if not marca or not marca.get("ejecutado", True):
            return
        marca["ejecutado"] = False
        marca["anulado"] = motivo
        marca["anulado_en"] = datetime.now().isoformat(timespec="seconds")
        bitacora.escribir_json_atomico(_registro_path(emp_id), registro)
        bitacora.registrar("registro_anulado", {"id": emp_id, "nombre": _NOMBRES.get(emp_id)},
                           tipo_marcaje=tipo_marcaje, motivo=motivo)
        logger.warning(f"[{emp_id}] Registro de {tipo_marcaje} ANULADO: {motivo}")
    except Exception as e:
        logger.error(f"[{emp_id}] Error anulando registro: {e}")


def tiempo_desde_ultimo_marcaje(emp_id: str) -> float:
    registro = leer_registro(emp_id)
    hoy = date.today().isoformat()
    timestamps = [v["timestamp"] for v in registro.get(hoy, {}).values()
                  if "timestamp" in v and v.get("ejecutado", True)]  # un marcaje anulado no cuenta para el cooldown
    if not timestamps:
        return float("inf")
    return datetime.now().timestamp() - max(timestamps)


# ---------------------------------------------------------------------------
# Verificación de estado con caché por empleado
# ---------------------------------------------------------------------------

def verificar_estado_emp(emp_id: str, empleado: Dict) -> Optional[str]:
    cache = get_cache()
    cache_key = f"estado_{emp_id}"

    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"[{emp_id}] Estado desde caché: {cached}")
        return cached

    try:
        estado = asyncio.run(verificar_estado(empleado=empleado))
        if estado:
            cache.set(estado, cache_key)
        return estado
    except Exception as e:
        logger.error(f"[{emp_id}] Error verificando estado: {e}")
        return None


# ---------------------------------------------------------------------------
# Alertas de fallo
# ---------------------------------------------------------------------------

def alertar_fallo(emp_nombre: str, tipo_marcaje: str, detalle: str = "no ejecutado") -> None:
    """Registra un fallo en alertas.log para monitoreo externo."""
    msg = f"{datetime.now().isoformat()} | ALERTA | {emp_nombre} | {tipo_marcaje} {detalle}\n"
    try:
        with open(alerta_file, "a", encoding="utf-8") as f:
            f.write(msg)
        bitacora.registrar("alerta", nombre=emp_nombre, mensaje=f"{tipo_marcaje} {detalle}")
        logger.error(f"🚨 ALERTA: [{emp_nombre}] {tipo_marcaje} {detalle} — ver {alerta_file.name}")
    except Exception as e:
        logger.error(f"Error escribiendo alerta: {e}")


# ---------------------------------------------------------------------------
# Ejecución de marcaje con todas las validaciones
# ---------------------------------------------------------------------------

def determinar_tipo_marcaje(accion: str, dia_semana: int) -> str:
    if dia_semana == 5:
        return "ENTRADA SÁBADO" if accion == "Entrada" else "SALIDA SÁBADO"
    return "ENTRADA SEMANA (L-V)" if accion == "Entrada" else "SALIDA SEMANA (L-V)"


def _portal_refleja_marcaje_completado(tipo_marcaje: str, boton_disponible: Optional[str]) -> bool:
    """Determina si el estado actual del portal implica que el marcaje ya fue realizado."""
    if not boton_disponible:
        return False

    # Si el portal muestra "Salida", significa que ya existe una entrada activa.
    if "ENTRADA" in tipo_marcaje and boton_disponible == "Salida":
        return True

    # Si el portal muestra "Entrada", significa que ya se cerró la jornada (salida hecha).
    if "SALIDA" in tipo_marcaje and boton_disponible == "Entrada":
        return True

    return False


def _programar_confirmacion(empleado: Dict, tipo_marcaje: str, accion: str,
                            demora: int = CONFIRMAR_DEMORA_SEG, intento: int = 1, reintento: int = 0) -> None:
    """Agenda la confirmación independiente de un marcaje (un segundo login al portal).

    `reintento` es el número del reintento de marcaje que originó este clic (0 = el original).
    """
    if not CONFIRMAR:
        return
    if _scheduler is None:  # marcaje hecho durante el arranque: se agenda cuando exista el scheduler
        _cola_confirmaciones.append((empleado, tipo_marcaje, accion, demora, intento, reintento))
        return
    try:
        _scheduler.add_job(
            partial(confirmar_marcaje_emp, empleado, tipo_marcaje, accion, intento, reintento),
            "date",
            run_date=datetime.now(_scheduler.timezone) + timedelta(seconds=demora),
            id=f"confirmar_{empleado['id']}_{tipo_marcaje}_{intento}",
            name=f"[{empleado['nombre']}] Confirmar {tipo_marcaje} (intento {intento})",
            replace_existing=True,
        )
    except Exception as e:
        logger.warning(f"[{empleado['nombre']}] No se pudo agendar la confirmación de {tipo_marcaje}: {e}")


def confirmar_marcaje_emp(empleado: Dict, tipo_marcaje: str, accion: str, intento: int = 1,
                          reintento: int = 0) -> None:
    """Segundo login independiente: comprueba en el portal que el marcaje realmente quedó.

    Si el portal SIGUE ofreciendo el botón, el marcaje no quedó: se anula el registro local y se
    programa un reintento (no puede duplicar, porque solo se vuelve a hacer clic si un login nuevo
    sigue viendo ese botón). Agotados los reintentos, deja la alerta.
    """
    emp_id, emp_nombre = empleado["id"], empleado["nombre"]
    tag = f"[{emp_nombre}]"
    get_cache().invalidar(f"estado_{emp_id}")
    try:
        boton = asyncio.run(verificar_estado(empleado=empleado))
    except Exception as e:
        logger.error(f"{tag} Error confirmando {tipo_marcaje}: {e}")
        boton = None

    confirmada = confirmacion_de(accion, boton)
    bitacora.registrar("confirmacion", empleado, accion=accion, tipo_marcaje=tipo_marcaje,
                       confirmada=confirmada, boton=boton, intento=intento)

    if confirmada is True:
        logger.info(f"{tag} ✅ {tipo_marcaje} CONFIRMADO por el portal (ahora ofrece '{boton}')")
    elif confirmada is False:
        logger.error(f"{tag} ❌ {tipo_marcaje} NO confirmado: el portal sigue ofreciendo '{boton}'")
        anular_registro(emp_id, tipo_marcaje, "el portal sigue ofreciendo el botón de esa acción")
        if not _programar_reintento(empleado, tipo_marcaje, accion, reintento + 1):
            alertar_fallo(emp_nombre, tipo_marcaje, "NO CONFIRMADO por el portal")
    else:
        logger.warning(f"{tag} ⚠️ Confirmación de {tipo_marcaje} no concluyente (botón: {boton})")
        if intento < 2:
            _programar_confirmacion(empleado, tipo_marcaje, accion, demora=300, intento=intento + 1,
                                    reintento=reintento)


def _hora_programada(empleado: Dict, accion: str, dia: date) -> time:
    h = obtener_horario_dia(empleado["horario"], dia.weekday())
    return time(h["entrada_hora"], h["entrada_minuto"]) if accion == "Entrada" else time(h["salida_hora"], h["salida_minuto"])


def _programar_reintento(empleado: Dict, tipo_marcaje: str, accion: str, reintento: int) -> bool:
    """Agenda el reintento número `reintento` de un marcaje que el portal no registró.

    Devuelve False (y no agenda nada) si ya no corresponde: reintentos agotados o desactivados, o
    fuera de la franja horaria del marcaje. El llamador debe entonces dejar la alerta.
    """
    tag = f"[{empleado['nombre']}]"
    hoy = date.today()
    ok, motivo = puede_reintentar(datetime.now(), _hora_programada(empleado, accion, hoy), reintento, REINTENTOS_MAX)
    if not ok:
        logger.warning(f"{tag} No se reintenta {tipo_marcaje}: {motivo}")
        return False
    if _scheduler is None:  # durante el arranque: se agenda cuando exista el scheduler
        _cola_reintentos.append((empleado, tipo_marcaje, accion, reintento))
        return True
    try:
        _scheduler.add_job(
            partial(reintentar_marcaje_emp, empleado, tipo_marcaje, accion, reintento),
            "date",
            run_date=datetime.now(_scheduler.timezone) + timedelta(seconds=REINTENTO_DEMORA_SEG),
            id=f"reintento_{empleado['id']}_{tipo_marcaje}_{reintento}",
            name=f"[{empleado['nombre']}] Reintento {reintento} de {tipo_marcaje}",
            replace_existing=True,
        )
    except Exception as e:
        logger.warning(f"{tag} No se pudo agendar el reintento de {tipo_marcaje}: {e}")
        return False
    bitacora.registrar("reintento_programado", empleado, tipo_marcaje=tipo_marcaje, reintento=reintento,
                       en_seg=REINTENTO_DEMORA_SEG)
    logger.warning(f"{tag} 🔁 {tipo_marcaje} no quedó en el portal: reintento {reintento}/{REINTENTOS_MAX} "
                   f"en {REINTENTO_DEMORA_SEG} s")
    return True


def reintentar_marcaje_emp(empleado: Dict, tipo_marcaje: str, accion: str, reintento: int) -> None:
    """Vuelve a intentar un marcaje que el portal no registró.

    El registro local NO manda aquí: manda el portal. run() solo hace clic si el portal ofrece el
    botón esperado, y un botón ofrecido significa que ese marcaje no existe, así que no duplica.
    """
    emp_id, emp_nombre = empleado["id"], empleado["nombre"]
    tag = f"[{emp_nombre}]"
    hoy = date.today()
    if es_festivo(hoy) or hoy.weekday() == 6:
        return
    get_cache().invalidar(f"estado_{emp_id}")
    logger.warning(f"{tag} 🔁 Reintento {reintento}/{REINTENTOS_MAX} de {tipo_marcaje}")
    try:
        resultado = asyncio.run(run(accion_esperada=accion, empleado=empleado))
    except Exception as e:
        logger.error(f"{tag} Error en el reintento de {tipo_marcaje}: {e}")
        resultado = None
    bitacora.registrar("reintento", empleado, tipo_marcaje=tipo_marcaje, reintento=reintento,
                       resultado="ok" if resultado else "no_realizado")

    if resultado:
        tipo_real = determinar_tipo_marcaje(resultado, hoy.weekday())
        guardar_registro(emp_id, tipo_real, 0)
        logger.info(f"{tag} ✅ Reintento {reintento} completado: {resultado} — guardado como '{tipo_real}'")
        _programar_confirmacion(empleado, tipo_real, resultado, reintento=reintento)
        return

    get_cache().invalidar(f"estado_{emp_id}")
    boton = verificar_estado_emp(emp_id, empleado)
    if _portal_refleja_marcaje_completado(tipo_marcaje, boton):
        guardar_registro(emp_id, tipo_marcaje, 0, origen="portal")
        logger.info(f"{tag} ℹ️ El portal ya refleja {tipo_marcaje} (botón: {boton}) — sincronizado")
        return
    if not _programar_reintento(empleado, tipo_marcaje, accion, reintento + 1):
        alertar_fallo(emp_nombre, tipo_marcaje, f"no se pudo marcar tras {reintento} reintento(s)")


def ejecutar_marcaje_emp(
    empleado: Dict,
    tipo_marcaje: str,
    variacion_minutos: int = 0,
    validar_horario: bool = True,
) -> Optional[str]:
    emp_id = empleado["id"]
    emp_nombre = empleado["nombre"]
    horario = empleado["horario"]
    hoy = date.today()
    ahora = datetime.now()
    tag = f"[{emp_nombre}]"

    logger.info("=" * 80)
    logger.info(f"{tag} Intento de marcaje: {tipo_marcaje}")
    logger.info(f"{tag} Fecha: {hoy} | Hora: {ahora.strftime('%H:%M:%S')}")

    if ya_se_ejecuto_hoy(emp_id, tipo_marcaje):
        logger.warning(f"{tag} {tipo_marcaje} YA EJECUTADO HOY — omitiendo")
        logger.info("=" * 80)
        return None

    segundos = tiempo_desde_ultimo_marcaje(emp_id)
    if segundos < HorarioConfig.COOLDOWN_ENTRE_MARCAJES:
        logger.warning(f"{tag} COOLDOWN ACTIVO: {segundos:.0f}s desde último marcaje")
        logger.info("=" * 80)
        return None

    if es_festivo(hoy):
        logger.warning(f"{tag} HOY ES FESTIVO — omitiendo")
        logger.info("=" * 80)
        return None

    if hoy.weekday() == 6:
        logger.warning(f"{tag} HOY ES DOMINGO — omitiendo")
        logger.info("=" * 80)
        return None

    # Determinar acción y hora programada según el día actual
    h_dia = obtener_horario_dia(horario, hoy.weekday())
    if "ENTRADA" in tipo_marcaje:
        accion_esperada = "Entrada"
        hora_prog = time(h_dia["entrada_hora"], h_dia["entrada_minuto"])
    else:
        accion_esperada = "Salida"
        hora_prog = time(h_dia["salida_hora"], h_dia["salida_minuto"])

    if validar_horario:
        hora_actual = ahora.time()
        hora_min = (datetime.combine(hoy, hora_prog) - timedelta(minutes=30)).time()
        hora_max = (datetime.combine(hoy, hora_prog) + timedelta(minutes=30)).time()
        if not (hora_min <= hora_actual <= hora_max):
            logger.warning(
                f"{tag} FUERA DE HORARIO — actual: {hora_actual.strftime('%H:%M')}, "
                f"programado: {hora_prog.strftime('%H:%M')} "
                f"(ventana: {hora_min.strftime('%H:%M')}–{hora_max.strftime('%H:%M')})"
            )
            logger.info("=" * 80)
            return None

    logger.info(f"{tag} Validaciones OK — ejecutando {tipo_marcaje}...")

    try:
        accion = asyncio.run(run(accion_esperada=accion_esperada, empleado=empleado))

        if accion:
            tipo_real = determinar_tipo_marcaje(accion, hoy.weekday())
            guardar_registro(emp_id, tipo_real, variacion_minutos)
            logger.info(f"{tag} ✅ Marcaje completado: {accion} — guardado como '{tipo_real}'")
            _programar_confirmacion(empleado, tipo_real, accion)
        else:
            # Revalidar estado del portal para evitar falsos negativos por ejecuciones
            # concurrentes o marcajes manuales ya realizados.
            get_cache().invalidar(f"estado_{emp_id}")
            boton = verificar_estado_emp(emp_id, empleado)
            if _portal_refleja_marcaje_completado(tipo_marcaje, boton):
                guardar_registro(emp_id, tipo_marcaje, variacion_minutos, origen="portal")
                logger.info(
                    f"{tag} ℹ️ Marcaje ya reflejado en portal (botón: {boton}) — "
                    f"sincronizado como '{tipo_marcaje}'"
                )
                return accion_esperada

            logger.warning(f"{tag} ⚠️ Marcaje no ejecutado")
            # Si el portal sigue ofreciendo ese botón, el marcaje no existe: se reintenta (sin alerta
            # todavía; la deja el último reintento si tampoco funciona).
            if boton == accion_esperada and _programar_reintento(empleado, tipo_marcaje, accion_esperada, 1):
                return accion
            alertar_fallo(emp_nombre, tipo_marcaje)

        return accion

    except Exception as e:
        logger.error(f"{tag} Error ejecutando {tipo_marcaje}: {e}", exc_info=True)
        alertar_fallo(emp_nombre, tipo_marcaje)
        return None
    finally:
        logger.info("=" * 80)


# ---------------------------------------------------------------------------
# Funciones de job por empleado
# ---------------------------------------------------------------------------

def entrada_semana_emp(empleado: Dict) -> None:
    emp_id = empleado["id"]
    tipo = "ENTRADA SEMANA (L-V)"
    if ya_se_ejecuto_hoy(emp_id, tipo):
        logger.info(f"[{empleado['nombre']}] {tipo} ya ejecutada hoy — omitiendo")
        return
    ejecutar_marcaje_emp(empleado, tipo)


def salida_semana_emp(empleado: Dict) -> None:
    emp_id = empleado["id"]
    emp_nombre = empleado["nombre"]
    tipo_entrada = "ENTRADA SEMANA (L-V)"
    tipo_salida = "SALIDA SEMANA (L-V)"

    if ya_se_ejecuto_hoy(emp_id, tipo_salida):
        logger.info(f"[{emp_nombre}] {tipo_salida} ya ejecutada hoy — omitiendo")
        return

    if not ya_se_ejecuto_hoy(emp_id, tipo_entrada):
        get_cache().invalidar(f"estado_{emp_id}")
        boton = verificar_estado_emp(emp_id, empleado)
        if boton == "Salida":
            logger.info(f"[{emp_nombre}] Entrada detectada en GeoVictoria — sincronizando registro local")
            guardar_registro(emp_id, tipo_entrada, origen="portal")
        else:
            logger.warning(f"[{emp_nombre}] Salida omitida — no hay entrada previa registrada")
            return

    get_cache().invalidar(f"estado_{emp_id}")
    ejecutar_marcaje_emp(empleado, tipo_salida)


def entrada_sabado_emp(empleado: Dict) -> None:
    emp_id = empleado["id"]
    tipo = "ENTRADA SÁBADO"
    if ya_se_ejecuto_hoy(emp_id, tipo):
        logger.info(f"[{empleado['nombre']}] {tipo} ya ejecutada hoy — omitiendo")
        return
    ejecutar_marcaje_emp(empleado, tipo)


def salida_sabado_emp(empleado: Dict) -> None:
    emp_id = empleado["id"]
    emp_nombre = empleado["nombre"]
    tipo_entrada = "ENTRADA SÁBADO"
    tipo_salida = "SALIDA SÁBADO"

    if ya_se_ejecuto_hoy(emp_id, tipo_salida):
        logger.info(f"[{emp_nombre}] {tipo_salida} ya ejecutada hoy — omitiendo")
        return

    if not ya_se_ejecuto_hoy(emp_id, tipo_entrada):
        get_cache().invalidar(f"estado_{emp_id}")
        boton = verificar_estado_emp(emp_id, empleado)
        if boton == "Salida":
            logger.info(f"[{emp_nombre}] Entrada sábado detectada en GeoVictoria — sincronizando")
            guardar_registro(emp_id, tipo_entrada, origen="portal")
        else:
            logger.warning(f"[{emp_nombre}] Salida sábado omitida — no hay entrada previa")
            return

    get_cache().invalidar(f"estado_{emp_id}")
    ejecutar_marcaje_emp(empleado, tipo_salida)


def verificar_pendientes_emp(empleado: Dict) -> None:
    """Detecta y ejecuta marcajes pendientes para un empleado (PC iniciado tarde, etc.)."""
    emp_id = empleado["id"]
    emp_nombre = empleado["nombre"]
    horario = empleado["horario"]
    hoy = date.today()
    ahora = datetime.now()
    dia_semana = hoy.weekday()
    hora_actual = ahora.time()
    tag = f"[{emp_nombre}]"

    logger.info(f"\n{tag} VERIFICANDO PENDIENTES | {hoy.strftime('%A %d/%m/%Y')} {ahora.strftime('%H:%M')}")
    get_cache().invalidar(f"estado_{emp_id}")

    if es_festivo(hoy):
        logger.info(f"{tag} Festivo — sin pendientes")
        return
    if dia_semana == 6:
        logger.info(f"{tag} Domingo — sin pendientes")
        return
    if dia_semana == 5 and not horario.get("trabaja_sabados", True):
        logger.info(f"{tag} No trabaja sábados — omitiendo")
        return

    if dia_semana == 5:
        tipo_entrada = "ENTRADA SÁBADO"
        tipo_salida = "SALIDA SÁBADO"
    else:
        tipo_entrada = "ENTRADA SEMANA (L-V)"
        tipo_salida = "SALIDA SEMANA (L-V)"

    h_dia = obtener_horario_dia(horario, dia_semana)
    hora_entrada = time(h_dia["entrada_hora"], h_dia["entrada_minuto"])
    hora_salida  = time(h_dia["salida_hora"],  h_dia["salida_minuto"])

    if ya_se_ejecuto_hoy(emp_id, tipo_entrada) and ya_se_ejecuto_hoy(emp_id, tipo_salida):
        logger.info(f"{tag} Ambos marcajes completados hoy")
        return

    # --- Verificar entrada pendiente ---
    if hora_actual > hora_entrada and not ya_se_ejecuto_hoy(emp_id, tipo_entrada):
        boton = verificar_estado_emp(emp_id, empleado)
        if boton == "Salida":
            logger.info(f"{tag} {tipo_entrada} ya marcado manualmente — sincronizando registro")
            guardar_registro(emp_id, tipo_entrada, origen="portal")
        elif hora_actual <= time(12, 0):
            logger.warning(f"{tag} PENDIENTE: {tipo_entrada} — ejecutando ahora")
            ejecutar_marcaje_emp(empleado, tipo_entrada, validar_horario=False)
        else:
            logger.warning(f"{tag} MARCAJE PERDIDO: {tipo_entrada} — demasiado tarde (>12:00)")
            alertar_fallo(emp_nombre, tipo_entrada)

    # --- Verificar salida pendiente ---
    if hora_actual > hora_salida and not ya_se_ejecuto_hoy(emp_id, tipo_salida):
        if not ya_se_ejecuto_hoy(emp_id, tipo_entrada):
            boton = verificar_estado_emp(emp_id, empleado)
            if boton == "Salida":
                guardar_registro(emp_id, tipo_entrada, origen="portal")
            else:
                logger.warning(f"{tag} Salida omitida — no hay entrada previa")
                return

        if hora_actual <= time(23, 0):
            logger.warning(f"{tag} PENDIENTE: {tipo_salida} — ejecutando ahora")
            ejecutar_marcaje_emp(empleado, tipo_salida, validar_horario=False)
        else:
            logger.warning(f"{tag} MARCAJE PERDIDO: {tipo_salida} — demasiado tarde (>23:00)")
            alertar_fallo(emp_nombre, tipo_salida)



# ---------------------------------------------------------------------------
# Configuración de jobs por empleado en el scheduler
# ---------------------------------------------------------------------------

# Mapeo de weekday Python (0-4) → nombre APScheduler
_WEEKDAY_A_APSCHEDULER = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri"}


def _agrupar_dias_semana_por_horario(horario: Dict):
    """
    Agrupa los días L-V según su combinación (entrada, salida).
    Retorna lista de tuplas: ((eh, em, sh, sm), [lista de nombres APScheduler])
    Esto permite crear un solo CronTrigger por grupo de días con el mismo horario.
    """
    grupos: Dict = {}
    for wd, nombre_ap in _WEEKDAY_A_APSCHEDULER.items():
        h = obtener_horario_dia(horario, wd)
        clave = (h["entrada_hora"], h["entrada_minuto"], h["salida_hora"], h["salida_minuto"])
        grupos.setdefault(clave, []).append(nombre_ap)
    return list(grupos.items())


def configurar_trabajos_empleado(scheduler: BlockingScheduler, empleado: Dict, emp_index: int = 0) -> None:
    emp_id = empleado["id"]
    emp_nombre = empleado["nombre"]
    h = empleado["horario"]
    tag = f"[{emp_nombre}]"
    offset_s = emp_index * HorarioConfig.STAGGER_SEGUNDOS

    logger.info(f"{tag} Configurando horarios (offset +{offset_s}s):")

    # --- Días de semana (L-V), agrupados por combinación de horario ---
    grupos = _agrupar_dias_semana_por_horario(h)
    for gidx, ((eh, em, sh, sm), dias_ap) in enumerate(grupos):
        dias_str = ",".join(dias_ap)
        # Sufijo numérico solo cuando hay más de un grupo (horario diferenciado por día)
        sufijo = f"_g{gidx}" if len(grupos) > 1 else ""

        feh, fem, fes = _aplicar_offset(eh, em, offset_s)
        fsh, fsm, fss = _aplicar_offset(sh, sm, offset_s)

        scheduler.add_job(
            partial(entrada_semana_emp, empleado),
            CronTrigger(day_of_week=dias_str, hour=feh, minute=fem, second=fes, timezone="America/Bogota"),
            id=f"entrada_semana_{emp_id}{sufijo}",
            name=f"[{emp_nombre}] Entrada {dias_str} {feh:02d}:{fem:02d}:{fes:02d}",
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            partial(salida_semana_emp, empleado),
            CronTrigger(day_of_week=dias_str, hour=fsh, minute=fsm, second=fss, timezone="America/Bogota"),
            id=f"salida_semana_{emp_id}{sufijo}",
            name=f"[{emp_nombre}] Salida {dias_str} {fsh:02d}:{fsm:02d}:{fss:02d}",
            max_instances=1,
            coalesce=True,
        )
        logger.info(f"  {tag} ✓ Entrada {dias_str}: {feh:02d}:{fem:02d}:{fes:02d} | Salida: {fsh:02d}:{fsm:02d}:{fss:02d}")
        for dia in dias_ap:
            _PLAN.setdefault(emp_id, {})[dia] = {
                "entrada": f"{feh:02d}:{fem:02d}:{fes:02d}", "salida": f"{fsh:02d}:{fsm:02d}:{fss:02d}"}

    # --- Sábado (opcional) ---
    if h.get("trabaja_sabados", True):
        feh_s, fem_s, fes_s = _aplicar_offset(h["entrada_sabado_hora"], h["entrada_sabado_minuto"], offset_s)
        fsh_s, fsm_s, fss_s = _aplicar_offset(h["salida_sabado_hora"], h["salida_sabado_minuto"], offset_s)

        scheduler.add_job(
            partial(entrada_sabado_emp, empleado),
            CronTrigger(day_of_week="sat", hour=feh_s, minute=fem_s, second=fes_s, timezone="America/Bogota"),
            id=f"entrada_sabado_{emp_id}",
            name=f"[{emp_nombre}] Entrada Sáb {feh_s:02d}:{fem_s:02d}:{fes_s:02d}",
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            partial(salida_sabado_emp, empleado),
            CronTrigger(day_of_week="sat", hour=fsh_s, minute=fsm_s, second=fss_s, timezone="America/Bogota"),
            id=f"salida_sabado_{emp_id}",
            name=f"[{emp_nombre}] Salida Sáb {fsh_s:02d}:{fsm_s:02d}:{fss_s:02d}",
            max_instances=1,
            coalesce=True,
        )
        _PLAN.setdefault(emp_id, {})["sat"] = {
            "entrada": f"{feh_s:02d}:{fem_s:02d}:{fes_s:02d}", "salida": f"{fsh_s:02d}:{fsm_s:02d}:{fss_s:02d}"}
        logger.info(f"  {tag} ✓ Entrada/Salida Sábado configurados")

    # Verificación periódica escalonada dentro del minuto :05 (10s entre empleados)
    verificacion_segundo = (emp_index * 10) % 60
    scheduler.add_job(
        partial(verificar_pendientes_emp, empleado),
        CronTrigger(minute=5, second=verificacion_segundo, timezone="America/Bogota"),
        id=f"verificacion_{emp_id}",
        name=f"[{emp_nombre}] Verificación cada hora (:05:{verificacion_segundo:02d})",
        max_instances=1,
        coalesce=True,
    )
    logger.info(f"  {tag} ✓ Verificación periódica: cada hora al :05:{verificacion_segundo:02d}")


# ---------------------------------------------------------------------------
# Lock file (previene múltiples instancias del programador)
# ---------------------------------------------------------------------------

def _pid_en_lock() -> Optional[int]:
    try:
        return int(lock_file.read_text().strip())
    except (OSError, ValueError):
        return None


def crear_lock_file() -> None:
    """Toma la exclusión de instancia única y deja el PID en el lock file (informativo).

    La exclusión real la da el sistema operativo (ver control_concurrencia), no el archivo:
    borrar el lock no permite arrancar un segundo programador.
    """
    try:
        adquirir_instancia_unica(guard_file)
    except InstanciaYaEnEjecucion:
        pid = _pid_en_lock()
        detalle = f" (PID {pid})" if pid else ""
        logger.error(f"❌ Programador ya en ejecución{detalle} — detenga esa instancia primero")
        sys.exit(1)

    lock_file.write_text(str(os.getpid()))
    logger.info(f"🔒 Lock creado: PID {os.getpid()}")


def eliminar_lock_file() -> None:
    try:
        # Solo si es el nuestro: un duplicado rechazado no debe borrar el lock del activo
        if _pid_en_lock() == os.getpid():
            lock_file.unlink()
            logger.info("🔓 Lock eliminado")
    except Exception as e:
        logger.error(f"Error eliminando lock: {e}")


# ---------------------------------------------------------------------------
# Listener de jobs
# ---------------------------------------------------------------------------

def _tick_scheduler() -> None:
    """Job periódico: prueba de que el scheduler y su pool de hilos siguen respondiendo."""
    global _ULTIMO_TICK
    _ULTIMO_TICK = datetime.now().isoformat(timespec="seconds")


def _iniciar_latido() -> None:
    """Hilo que escribe el latido cada 20 s desde el arranque (también mientras revisa pendientes)."""
    def bucle() -> None:
        espera = threading.Event()
        while True:
            bitacora.escribir_latido(_INICIO, _FASE, _PLAN, _ULTIMO_TICK)
            espera.wait(20)

    threading.Thread(target=bucle, name="latido", daemon=True).start()


def _preparar_scheduler(scheduler: BlockingScheduler) -> None:
    """Deja el scheduler disponible para agendar confirmaciones y añade el job de latido."""
    global _scheduler
    _scheduler = scheduler
    scheduler.add_job(_tick_scheduler, IntervalTrigger(seconds=20), id="tick_scheduler",
                      name="Latido del scheduler", max_instances=1, coalesce=True)
    pendientes = list(_cola_confirmaciones)
    _cola_confirmaciones.clear()
    for empleado, tipo, accion, demora, intento, reintento in pendientes:
        _programar_confirmacion(empleado, tipo, accion, demora=min(demora, 30), intento=intento, reintento=reintento)
    reintentos = list(_cola_reintentos)
    _cola_reintentos.clear()
    for empleado, tipo, accion, reintento in reintentos:
        _programar_reintento(empleado, tipo, accion, reintento)


def _reconciliar_confirmaciones(empleados: List[Dict]) -> int:
    """Agenda la confirmación de los marcajes de hoy que no llegaron a confirmarse.

    La confirmación es un job en memoria: si el programador se reinicia entre el marcaje y su
    confirmación (o el marcaje lo hizo una versión anterior), nadie la verificaría. Se escalonan 10 s
    para no abrir todos los navegadores a la vez. Nunca repite el marcaje, solo lo comprueba.
    """
    if not CONFIRMAR:
        return 0
    eventos = bitacora.leer_eventos()
    hoy = date.today().isoformat()
    agendadas = 0
    for emp in empleados:
        try:
            registro_hoy = leer_registro(emp["id"]).get(hoy, {})
            for tipo, accion in marcajes_sin_confirmar(registro_hoy, eventos, emp["id"]):
                _programar_confirmacion(emp, tipo, accion, demora=30 + 10 * agendadas)
                agendadas += 1
        except Exception as e:
            logger.warning(f"[{emp.get('nombre', emp.get('id'))}] No se pudo reconciliar confirmaciones: {e}")
    if agendadas:
        logger.info(f"🔎 {agendadas} marcaje(s) de hoy sin confirmar: se verificarán en el portal")
    return agendadas


def _marcar_fase_activa() -> None:
    global _FASE
    _FASE = "activo"
    _tick_scheduler()
    bitacora.escribir_latido(_INICIO, _FASE, _PLAN, _ULTIMO_TICK)


def job_listener(event) -> None:
    if event.exception:
        logger.error(f"❌ Error en job '{event.job_id}': {event.exception}")
    else:
        logger.debug(f"✅ Job completado: {event.job_id}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Redirigir stderr al log para capturar excepciones no manejadas
    try:
        sys.stderr = open(log_file, "a", encoding="utf-8", errors="replace")
    except Exception:
        pass  # Si falla, seguir con stderr original

    desactivar_seleccion_consola()  # un clic en la ventana no debe congelar el scheduler
    crear_lock_file()
    atexit.register(eliminar_lock_file)
    _iniciar_latido()
    atexit.register(lambda: bitacora.registrar("programador_fin"))

    logger.info("\n" + "=" * 80)
    logger.info("🚀 INICIANDO PROGRAMADOR GEOVICTORIA — SOPORTE MULTI-EMPLEADO")
    logger.info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    try:
        empleados = cargar_empleados()
    except ValueError as e:
        logger.error(f"❌ Error cargando empleados: {e}")
        sys.exit(1)

    logger.info(f"👥 Empleados activos: {len(empleados)}")
    _NOMBRES.update({e["id"]: e["nombre"] for e in empleados})
    bitacora.registrar("programador_inicio", empleados=len(empleados))
    for emp in empleados:
        h = emp["horario"]
        logger.info(
            f"  • [{emp['id']}] {emp['nombre']} — "
            f"L-V {h['entrada_semana_hora']:02d}:{h['entrada_semana_minuto']:02d}/"
            f"{h['salida_semana_hora']:02d}:{h['salida_semana_minuto']:02d}"
        )

    listar_festivos_año(datetime.now().year)

    # Verificar pendientes al inicio (caso PC iniciado tarde)
    logger.info("\n🔍 Verificando marcajes pendientes al inicio...")
    for emp in empleados:
        try:
            verificar_pendientes_emp(emp)
        except Exception as e:
            logger.error(f"❌ Error verificando pendientes de {emp.get('nombre', emp.get('id'))}: {e}", exc_info=True)

    # Crear y configurar scheduler
    # Los jobs pueden quedar esperando cupo de navegador (control_concurrencia): más hilos que el
    # defecto (10) para que esperar no deje sin hilo a otros jobs, y 5 min de gracia para que un
    # job retrasado se ejecute en vez de descartarse (APScheduler usa 1 s por defecto).
    scheduler = BlockingScheduler(
        timezone="America/Bogota",
        executors={"default": ThreadPoolExecutor(20)},
        job_defaults={"misfire_grace_time": 300},
    )
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    _preparar_scheduler(scheduler)
    _reconciliar_confirmaciones(empleados)

    for idx, emp in enumerate(empleados):
        try:
            configurar_trabajos_empleado(scheduler, emp, emp_index=idx)
        except Exception as e:
            logger.error(f"❌ Error configurando trabajos de {emp.get('nombre', emp.get('id'))}: {e}", exc_info=True)

    # Nota: get_jobs() devuelve lista vacía antes de start() (APScheduler guarda
    # los jobs en _pending_jobs hasta que arranca). Mostramos la config manual.
    logger.info("\n📋 TRABAJOS CONFIGURADOS (se activan al arrancar):")
    logger.info("=" * 80)
    for emp in empleados:
        h = emp["horario"]
        logger.info(f"  [{emp['id']}] {emp['nombre']}")
        logger.info(f"       Entrada L-V: {h['entrada_semana_hora']:02d}:{h['entrada_semana_minuto']:02d}  |  Salida L-V: {h['salida_semana_hora']:02d}:{h['salida_semana_minuto']:02d}")
        if h.get("trabaja_sabados", True):
            logger.info(f"       Entrada Sab: {h['entrada_sabado_hora']:02d}:{h['entrada_sabado_minuto']:02d}  |  Salida Sab: {h['salida_sabado_hora']:02d}:{h['salida_sabado_minuto']:02d}")
    logger.info("=" * 80)

    logger.info(f"\n⏰ Programador activo con {len(empleados)} empleado(s). Ctrl+C para detener.\n")

    _marcar_fase_activa()
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n👋 Programador detenido por el usuario")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"❌ Error inesperado en el scheduler: {e}", exc_info=True)
        logger.error("❌ El programador se detuvo inesperadamente — revisar el log")
        raise


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        # Último recurso: loguear al archivo directamente
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                import traceback
                f.write(f"\n{'='*80}\n")
                f.write(f"EXCEPCION FATAL EN main():\n")
                f.write(traceback.format_exc())
                f.write(f"{'='*80}\n")
        except Exception:
            pass
        sys.exit(1)
