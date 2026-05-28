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
from datetime import date, datetime, time, timedelta
from functools import partial
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cache_estado import get_cache
from src.empleados import cargar_empleados, obtener_horario_dia
from src.festivos_colombia import es_festivo, listar_festivos_año
from src.geovictoria import run, verificar_estado

# ---------------------------------------------------------------------------
# Paths de archivos de estado
# ---------------------------------------------------------------------------

log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
lock_file = log_dir / "programador.lock"
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
    STAGGER_SEGUNDOS = 30         # separación entre empleados con el mismo horario


def _aplicar_offset(hora: int, minuto: int, offset_segundos: int):
    """Convierte hora:minuto + offset en (hora, minuto, segundo) sin desbordamiento."""
    total = hora * 3600 + minuto * 60 + offset_segundos
    return total // 3600, (total % 3600) // 60, total % 60


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
    except Exception as e:
        logger.warning(f"[{emp_id}] Error leyendo registro: {e}")
    return {}


def guardar_registro(emp_id: str, tipo_marcaje: str, variacion_minutos: int = 0) -> None:
    try:
        registro = leer_registro(emp_id)
        hoy = date.today().isoformat()
        ahora = datetime.now()

        registro.setdefault(hoy, {})[tipo_marcaje] = {
            "ejecutado": True,
            "hora": ahora.isoformat(),
            "timestamp": ahora.timestamp(),
            "variacion_minutos": variacion_minutos,
        }

        # Mantener solo los últimos 30 días
        for fecha in sorted(registro.keys(), reverse=True)[30:]:
            del registro[fecha]

        with open(_registro_path(emp_id), "w", encoding="utf-8") as f:
            json.dump(registro, f, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"[{emp_id}] Error guardando registro: {e}")


def ya_se_ejecuto_hoy(emp_id: str, tipo_marcaje: str) -> bool:
    registro = leer_registro(emp_id)
    hoy = date.today().isoformat()
    return registro.get(hoy, {}).get(tipo_marcaje, {}).get("ejecutado", False)


def tiempo_desde_ultimo_marcaje(emp_id: str) -> float:
    registro = leer_registro(emp_id)
    hoy = date.today().isoformat()
    timestamps = [v["timestamp"] for v in registro.get(hoy, {}).values() if "timestamp" in v]
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

def alertar_fallo(emp_nombre: str, tipo_marcaje: str) -> None:
    """Registra un fallo en alertas.log para monitoreo externo."""
    msg = f"{datetime.now().isoformat()} | ALERTA | {emp_nombre} | {tipo_marcaje} no ejecutado\n"
    try:
        with open(alerta_file, "a", encoding="utf-8") as f:
            f.write(msg)
        logger.error(f"🚨 ALERTA: [{emp_nombre}] {tipo_marcaje} — ver {alerta_file.name}")
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
        else:
            # Revalidar estado del portal para evitar falsos negativos por ejecuciones
            # concurrentes o marcajes manuales ya realizados.
            get_cache().invalidar(f"estado_{emp_id}")
            boton = verificar_estado_emp(emp_id, empleado)
            if _portal_refleja_marcaje_completado(tipo_marcaje, boton):
                guardar_registro(emp_id, tipo_marcaje, variacion_minutos)
                logger.info(
                    f"{tag} ℹ️ Marcaje ya reflejado en portal (botón: {boton}) — "
                    f"sincronizado como '{tipo_marcaje}'"
                )
                return accion_esperada

            logger.warning(f"{tag} ⚠️ Marcaje no ejecutado")
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
            guardar_registro(emp_id, tipo_entrada)
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
            guardar_registro(emp_id, tipo_entrada)
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
            guardar_registro(emp_id, tipo_entrada)
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
                guardar_registro(emp_id, tipo_entrada)
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

def crear_lock_file() -> None:
    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                pid = int(f.read().strip())

            import psutil
            if psutil.pid_exists(pid):
                logger.error(f"❌ Programador ya en ejecución (PID {pid}) — detenga esa instancia primero")
                sys.exit(1)
            else:
                logger.warning(f"⚠️ Lock obsoleto (PID {pid} no existe) — recreando")
                lock_file.unlink()

        except (ValueError, ImportError) as e:
            logger.warning(f"⚠️ No se pudo verificar lock existente ({e}) — recreando")
            lock_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"⚠️ Error verificando lock: {e} — recreando")
            lock_file.unlink(missing_ok=True)

    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))
    logger.info(f"🔒 Lock creado: PID {os.getpid()}")


def eliminar_lock_file() -> None:
    try:
        if lock_file.exists():
            lock_file.unlink()
            logger.info("🔓 Lock eliminado")
    except Exception as e:
        logger.error(f"Error eliminando lock: {e}")


# ---------------------------------------------------------------------------
# Listener de jobs
# ---------------------------------------------------------------------------

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

    crear_lock_file()
    atexit.register(eliminar_lock_file)

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
    scheduler = BlockingScheduler(timezone="America/Bogota")
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

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
