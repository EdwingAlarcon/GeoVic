"""
Programador automático para marcaje de asistencia GeoVictoria
Configurado para Colombia con manejo de festivos
"""
import asyncio
import logging
import sys
import json
import random
from datetime import datetime, date, time, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from pathlib import Path

# Agregar el directorio raíz al path para importaciones
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.geovictoria import run, verificar_estado
from src.festivos_colombia import es_dia_laborable, es_festivo, listar_festivos_año

# Configuración de logging y registro de ejecuciones
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"programador_{datetime.now().strftime('%Y%m%d')}.log"
registro_file = log_dir / "registro_ejecuciones.json"

# Configurar logging con manejo robusto para Task Scheduler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Asegurar que se reconfigure el logging
)
logger = logging.getLogger(__name__)

# Log inicial para confirmar que el logging funciona
logger.info(f"=" * 80)
logger.info(f"📝 Sistema de logging inicializado")
logger.info(f"📁 Archivo de log: {log_file}")
logger.info(f"=" * 80)

# Configuración de horarios
class HorarioConfig:
    """Configuración de horarios de marcaje"""
    # Lunes a Viernes
    ENTRADA_SEMANA_HORA = 7
    ENTRADA_SEMANA_MINUTO = 0
    SALIDA_SEMANA_HORA = 17  # 5 PM
    SALIDA_SEMANA_MINUTO = 0
    
    # Sábados
    ENTRADA_SABADO_HORA = 7
    ENTRADA_SABADO_MINUTO = 0
    SALIDA_SABADO_HORA = 13  # 1 PM
    SALIDA_SABADO_MINUTO = 0
    
    # Variación aleatoria (en minutos) - Comportamiento humano realista
    # Para entrada: ocasionalmente antes, usualmente puntual o poco tarde
    VARIACION_ENTRADA_MIN = -2
    VARIACION_ENTRADA_MAX = 8
    
    # Para salida: ocasionalmente antes, frecuentemente unos minutos tarde
    VARIACION_SALIDA_MIN = -3
    VARIACION_SALIDA_MAX = 12

def calcular_horario_aleatorio(hora_base, minuto_base, variacion_min, variacion_max):
    """Calcula un horario aleatorio dentro del rango especificado"""
    # Crear datetime base para hoy
    ahora = datetime.now()
    dt_base = datetime(ahora.year, ahora.month, ahora.day, hora_base, minuto_base)
    
    # Calcular variación aleatoria en minutos
    variacion_minutos = random.randint(variacion_min, variacion_max)
    
    # Aplicar variación
    dt_aleatorio = dt_base + timedelta(minutes=variacion_minutos)
    
    logger.info(f"⏰ Horario base: {dt_base.strftime('%H:%M')}")
    logger.info(f"🎲 Variación aplicada: {variacion_minutos:+d} minutos")
    logger.info(f"🕐 Horario calculado: {dt_aleatorio.strftime('%H:%M')}")
    
    return dt_aleatorio.time(), variacion_minutos

def leer_registro_ejecuciones():
    """Lee el registro de ejecuciones del archivo JSON"""
    try:
        if registro_file.exists():
            with open(registro_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error leyendo registro de ejecuciones: {e}")
    return {}

def guardar_registro_ejecucion(tipo_marcaje: str, variacion_minutos: int = 0):
    """Guarda en el registro que se ejecutó un marcaje"""
    try:
        registro = leer_registro_ejecuciones()
        hoy = date.today().isoformat()
        ahora = datetime.now().isoformat()
        
        if hoy not in registro:
            registro[hoy] = {}
        
        registro[hoy][tipo_marcaje] = {
            'ejecutado': True,
            'hora': ahora,
            'variacion_minutos': variacion_minutos
        }
        
        # Limpiar registros antiguos (mantener solo últimos 30 días)
        fechas = sorted(registro.keys(), reverse=True)
        if len(fechas) > 30:
            for fecha_antigua in fechas[30:]:
                del registro[fecha_antigua]
        
        with open(registro_file, 'w', encoding='utf-8') as f:
            json.dump(registro, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Registro guardado: {tipo_marcaje} a las {ahora}")
    except Exception as e:
        logger.error(f"Error guardando registro de ejecución: {e}")

def ya_se_ejecuto_hoy(tipo_marcaje: str) -> bool:
    """Verifica si ya se ejecutó un tipo de marcaje hoy"""
    registro = leer_registro_ejecuciones()
    hoy = date.today().isoformat()
    
    if hoy in registro and tipo_marcaje in registro[hoy]:
        return registro[hoy][tipo_marcaje].get('ejecutado', False)
    
    return False

def determinar_tipo_marcaje(accion: str, dia_semana: int) -> str:
    """Determina el tipo de marcaje basado en la acción real ejecutada y el día"""
    if dia_semana == 5:  # Sábado
        if accion == "Entrada":
            return "ENTRADA SÁBADO"
        else:
            return "SALIDA SÁBADO"
    else:  # Lunes a Viernes
        if accion == "Entrada":
            return "ENTRADA SEMANA (L-V)"
        else:
            return "SALIDA SEMANA (L-V)"

def ejecutar_marcaje_con_validacion(tipo_marcaje: str, variacion_minutos: int = 0, validar_horario: bool = True):
    """
    Ejecutar marcaje solo si es día laborable, horario correcto y acción esperada coincide
    
    Args:
        tipo_marcaje: Tipo esperado (ENTRADA SEMANA, SALIDA SEMANA, etc.)
        variacion_minutos: Variación aleatoria aplicada
        validar_horario: Si True, valida que sea el horario apropiado para el tipo de marcaje
    """
    hoy = date.today()
    ahora = datetime.now()
    
    logger.info("=" * 80)
    logger.info(f"🔔 Intento de marcaje programado: {tipo_marcaje}")
    logger.info(f"📅 Fecha: {hoy.strftime('%A, %d de %B de %Y')}")
    logger.info(f"🕐 Hora: {ahora.strftime('%H:%M:%S')}")
    if variacion_minutos != 0:
        logger.info(f"🎲 Variación aleatoria: {variacion_minutos:+d} minutos")
    
    # Verificar si es festivo
    if es_festivo(hoy):
        logger.warning(f"🎉 HOY ES FESTIVO - No se ejecutará el marcaje")
        logger.info("=" * 80)
        return None
    
    # Verificar si es domingo
    if hoy.weekday() == 6:
        logger.warning(f"📅 HOY ES DOMINGO - No se ejecutará el marcaje")
        logger.info("=" * 80)
        return None
    
    # Verificación adicional para sábados
    if hoy.weekday() == 5:
        logger.info(f"📅 Hoy es sábado - Horario especial activo")
    
    # Determinar acción esperada y horarios
    if "ENTRADA" in tipo_marcaje:
        accion_esperada = "Entrada"
        if hoy.weekday() == 5:  # Sábado
            hora_programada = time(HorarioConfig.ENTRADA_SABADO_HORA, HorarioConfig.ENTRADA_SABADO_MINUTO)
        else:
            hora_programada = time(HorarioConfig.ENTRADA_SEMANA_HORA, HorarioConfig.ENTRADA_SEMANA_MINUTO)
    else:  # SALIDA
        accion_esperada = "Salida"
        if hoy.weekday() == 5:  # Sábado
            hora_programada = time(HorarioConfig.SALIDA_SABADO_HORA, HorarioConfig.SALIDA_SABADO_MINUTO)
        else:
            hora_programada = time(HorarioConfig.SALIDA_SEMANA_HORA, HorarioConfig.SALIDA_SEMANA_MINUTO)
    
    # Validar horario si está habilitado
    if validar_horario:
        hora_actual = ahora.time()
        # Permitir marcaje si estamos en la hora programada +/- 30 minutos
        hora_min = (datetime.combine(hoy, hora_programada) - timedelta(minutes=30)).time()
        hora_max = (datetime.combine(hoy, hora_programada) + timedelta(minutes=30)).time()
        
        if not (hora_min <= hora_actual <= hora_max):
            logger.warning(f"⏰ FUERA DE HORARIO")
            logger.warning(f"   • Hora actual: {hora_actual.strftime('%H:%M')}")
            logger.warning(f"   • Hora programada: {hora_programada.strftime('%H:%M')}")
            logger.warning(f"   • Ventana permitida: {hora_min.strftime('%H:%M')} - {hora_max.strftime('%H:%M')}")
            logger.warning(f"   • NO se ejecutará {tipo_marcaje}")
            logger.info("=" * 80)
            return None
        
        logger.info(f"✅ Horario válido para {accion_esperada}")
    
    # Si llegamos aquí, es día laborable y horario correcto
    logger.info(f"✅ Validaciones OK - Ejecutando {tipo_marcaje}...")
    
    try:
        # Ejecutar el marcaje CON VALIDACIÓN de acción esperada
        accion_ejecutada = asyncio.run(run(accion_esperada=accion_esperada))
        
        if accion_ejecutada:
            logger.info(f"✅ Marcaje completado: {accion_ejecutada}")
            
            # Registrar la acción REAL ejecutada, no la esperada
            tipo_real = determinar_tipo_marcaje(accion_ejecutada, hoy.weekday())
            guardar_registro_ejecucion(tipo_real, variacion_minutos)
            logger.info(f"💾 Registro guardado: {tipo_real}")
            
        else:
            logger.warning(f"⚠️ No se pudo ejecutar marcaje")
            
        return accion_ejecutada
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando {tipo_marcaje}: {e}", exc_info=True)
        return None
    finally:
        logger.info("=" * 80)

def entrada_semana():
    """Marcaje de entrada Lunes a Viernes con variación aleatoria calculada al ejecutar"""
    # Calcular variación aleatoria AL MOMENTO DE EJECUTAR
    variacion_minutos = random.randint(HorarioConfig.VARIACION_ENTRADA_MIN, HorarioConfig.VARIACION_ENTRADA_MAX)
    logger.info(f"🎲 Variación calculada para entrada: {variacion_minutos:+d} minutos")
    
    # Esperar la variación antes de ejecutar
    if variacion_minutos > 0:
        logger.info(f"⏳ Esperando {variacion_minutos} minutos antes de marcar entrada...")
        import time
        time.sleep(variacion_minutos * 60)
    elif variacion_minutos < 0:
        # Variación negativa ya fue aplicada por programarse antes
        logger.info(f"✅ Marcaje adelantado {abs(variacion_minutos)} minutos")
    
    ejecutar_marcaje_con_validacion("ENTRADA SEMANA (L-V)", variacion_minutos)

def salida_semana():
    """Marcaje de salida Lunes a Viernes con variación aleatoria calculada al ejecutar"""
    # Calcular variación aleatoria AL MOMENTO DE EJECUTAR
    variacion_minutos = random.randint(HorarioConfig.VARIACION_SALIDA_MIN, HorarioConfig.VARIACION_SALIDA_MAX)
    logger.info(f"🎲 Variación calculada para salida: {variacion_minutos:+d} minutos")
    
    # Esperar la variación antes de ejecutar
    if variacion_minutos > 0:
        logger.info(f"⏳ Esperando {variacion_minutos} minutos antes de marcar salida...")
        import time
        time.sleep(variacion_minutos * 60)
    elif variacion_minutos < 0:
        logger.info(f"✅ Marcaje adelantado {abs(variacion_minutos)} minutos")
    
    ejecutar_marcaje_con_validacion("SALIDA SEMANA (L-V)", variacion_minutos)

def entrada_sabado():
    """Marcaje de entrada Sábados con variación aleatoria calculada al ejecutar"""
    # Calcular variación aleatoria AL MOMENTO DE EJECUTAR
    variacion_minutos = random.randint(HorarioConfig.VARIACION_ENTRADA_MIN, HorarioConfig.VARIACION_ENTRADA_MAX)
    logger.info(f"🎲 Variación calculada para entrada sábado: {variacion_minutos:+d} minutos")
    
    # Esperar la variación antes de ejecutar
    if variacion_minutos > 0:
        logger.info(f"⏳ Esperando {variacion_minutos} minutos antes de marcar entrada...")
        import time
        time.sleep(variacion_minutos * 60)
    elif variacion_minutos < 0:
        logger.info(f"✅ Marcaje adelantado {abs(variacion_minutos)} minutos")
    
    ejecutar_marcaje_con_validacion("ENTRADA SÁBADO", variacion_minutos)

def salida_sabado():
    """Marcaje de salida Sábados con variación aleatoria calculada al ejecutar"""
    # Calcular variación aleatoria AL MOMENTO DE EJECUTAR
    variacion_minutos = random.randint(HorarioConfig.VARIACION_SALIDA_MIN, HorarioConfig.VARIACION_SALIDA_MAX)
    logger.info(f"🎲 Variación calculada para salida sábado: {variacion_minutos:+d} minutos")
    
    # Esperar la variación antes de ejecutar
    if variacion_minutos > 0:
        logger.info(f"⏳ Esperando {variacion_minutos} minutos antes de marcar salida...")
        import time
        time.sleep(variacion_minutos * 60)
    elif variacion_minutos < 0:
        logger.info(f"✅ Marcaje adelantado {abs(variacion_minutos)} minutos")
    
    ejecutar_marcaje_con_validacion("SALIDA SÁBADO", variacion_minutos)

def verificar_marcajes_pendientes():
    """Verifica y ejecuta marcajes pendientes consultando el estado real de GeoVictoria"""
    hoy = date.today()
    ahora = datetime.now()
    dia_semana = hoy.weekday()
    hora_actual = ahora.time()
    
    logger.info("\n" + "=" * 80)
    logger.info("🔍 VERIFICANDO MARCAJES PENDIENTES")
    logger.info(f"📅 Fecha: {hoy.strftime('%A, %d de %B de %Y')}")
    logger.info(f"🕐 Hora actual: {ahora.strftime('%H:%M:%S')}")
    logger.info("=" * 80)
    
    # No verificar si es domingo o festivo
    if es_festivo(hoy):
        logger.info("🎉 Hoy es festivo - No hay marcajes pendientes")
        logger.info("=" * 80)
        return
    
    if dia_semana == 6:  # Domingo
        logger.info("📅 Hoy es domingo - No hay marcajes pendientes")
        logger.info("=" * 80)
        return
    
    # Determinar horarios y tipos de marcaje según el día
    if dia_semana == 5:  # Sábado
        hora_entrada = time(HorarioConfig.ENTRADA_SABADO_HORA, HorarioConfig.ENTRADA_SABADO_MINUTO)
        hora_salida = time(HorarioConfig.SALIDA_SABADO_HORA, HorarioConfig.SALIDA_SABADO_MINUTO)
        tipo_entrada = "ENTRADA SÁBADO"
        tipo_salida = "SALIDA SÁBADO"
    else:  # Lunes a Viernes
        hora_entrada = time(HorarioConfig.ENTRADA_SEMANA_HORA, HorarioConfig.ENTRADA_SEMANA_MINUTO)
        hora_salida = time(HorarioConfig.SALIDA_SEMANA_HORA, HorarioConfig.SALIDA_SEMANA_MINUTO)
        tipo_entrada = "ENTRADA SEMANA (L-V)"
        tipo_salida = "SALIDA SEMANA (L-V)"
    
    marcajes_ejecutados = 0
    
    # PROTECCIÓN: Si ambos marcajes ya se ejecutaron hoy, no hacer nada
    if ya_se_ejecuto_hoy(tipo_entrada) and ya_se_ejecuto_hoy(tipo_salida):
        logger.info(f"✅ Ambos marcajes completados hoy ({tipo_entrada} y {tipo_salida})")
        logger.info("✅ No hay marcajes pendientes ni correcciones necesarias")
        logger.info("=" * 80)
        return
    
    # Verificar entrada pendiente
    if hora_actual > hora_entrada:
        # Primero verificar si ya se registró localmente
        if ya_se_ejecuto_hoy(tipo_entrada):
            logger.info(f"✅ {tipo_entrada} ya fue ejecutado hoy (según registro local)")
            # NO verificar inconsistencias si la entrada ya está registrada
            # Esto evita re-ejecuciones innecesarias
        else:
            # Validar que tenga sentido marcar entrada según la hora actual
            # No marcar entrada después de las 12 PM (mediodía)
            hora_limite_entrada = time(12, 0)
            
            if hora_actual > hora_limite_entrada:
                logger.warning(f"⚠️ MARCAJE PENDIENTE OMITIDO: {tipo_entrada}")
                logger.warning(f"   • Hora programada: {hora_entrada.strftime('%H:%M')}")
                logger.warning(f"   • Hora actual: {hora_actual.strftime('%H:%M')}")
                logger.warning(f"   • RAZÓN: Demasiado tarde para marcar entrada (después de 12:00 PM)")
                logger.warning(f"   • ACCIÓN: No se ejecutará para evitar marcajes incorrectos")
            else:
                logger.warning(f"⚠️ MARCAJE PENDIENTE DETECTADO: {tipo_entrada}")
                logger.info(f"   • Hora programada: {hora_entrada.strftime('%H:%M')}")
                logger.info(f"   • Hora actual: {hora_actual.strftime('%H:%M')}")
                logger.info(f"   • El PC probablemente se inició tarde")
                logger.info("   • Ejecutando marcaje pendiente...")
                logger.info("=" * 80)
                
                # NO validar horario en marcajes pendientes por PC encendido tarde
                ejecutar_marcaje_con_validacion(tipo_entrada, validar_horario=False)
                marcajes_ejecutados += 1
    else:
        logger.info(f"⏰ Aún no es hora de marcar entrada (programado: {hora_entrada.strftime('%H:%M')})")
    
    # Verificar salida pendiente
    if hora_actual > hora_salida:
        if not ya_se_ejecuto_hoy(tipo_salida):
            # Validar que la entrada ya se haya marcado
            if not ya_se_ejecuto_hoy(tipo_entrada):
                logger.warning(f"⚠️ MARCAJE PENDIENTE OMITIDO: {tipo_salida}")
                logger.warning(f"   • No se puede marcar salida sin entrada previa")
                logger.warning(f"   • ACCIÓN: Omitiendo marcaje de salida")
            else:
                # Validar que tenga sentido marcar salida según la hora actual
                # No marcar salida después de las 11 PM
                hora_limite_salida = time(23, 0)
                
                if hora_actual > hora_limite_salida:
                    logger.warning(f"⚠️ MARCAJE PENDIENTE OMITIDO: {tipo_salida}")
                    logger.warning(f"   • Hora programada: {hora_salida.strftime('%H:%M')}")
                    logger.warning(f"   • Hora actual: {hora_actual.strftime('%H:%M')}")
                    logger.warning(f"   • RAZÓN: Demasiado tarde para marcar salida (después de 11:00 PM)")
                    logger.warning(f"   • ACCIÓN: No se ejecutará para evitar marcajes incorrectos")
                else:
                    logger.warning(f"⚠️ MARCAJE PENDIENTE DETECTADO: {tipo_salida}")
                    logger.info(f"   • Hora programada: {hora_salida.strftime('%H:%M')}")
                    logger.info(f"   • Hora actual: {hora_actual.strftime('%H:%M')}")
                    logger.info(f"   • El PC probablemente se inició tarde")
                    logger.info("   • Ejecutando marcaje pendiente...")
                    logger.info("=" * 80)
                    
                    # NO validar horario en marcajes pendientes
                    ejecutar_marcaje_con_validacion(tipo_salida, validar_horario=False)
                    marcajes_ejecutados += 1
        else:
            logger.info(f"✅ {tipo_salida} ya fue ejecutado hoy (según registro local)")
            # NO verificar inconsistencias si la salida ya está registrada
            # Esto evita re-ejecuciones innecesarias
    else:
        logger.info(f"⏰ Aún no es hora de marcar salida (programado: {hora_salida.strftime('%H:%M')})")
    
    if marcajes_ejecutados == 0:
        logger.info("✅ No hay marcajes pendientes")
    
    logger.info("=" * 80)

def job_listener(event):
    """Escuchar eventos de trabajos"""
    if event.exception:
        logger.error(f"❌ Error en trabajo programado: {event.exception}")
    else:
        logger.debug(f"✅ Trabajo completado: {event.job_id}")

def configurar_trabajos_fijos(scheduler):
    """Configura los trabajos con horarios fijos - la variación se aplica al ejecutar"""
    logger.info("\n📅 CONFIGURANDO HORARIOS BASE:")
    logger.info("=" * 80)
    
    # LUNES A VIERNES - ENTRADA (horario base fijo, variación se aplica al ejecutar)
    scheduler.add_job(
        entrada_semana,
        CronTrigger(
            day_of_week='mon-fri',
            hour=HorarioConfig.ENTRADA_SEMANA_HORA,
            minute=HorarioConfig.ENTRADA_SEMANA_MINUTO,
            timezone='America/Bogota'
        ),
        id='entrada_semana',
        name=f'Entrada L-V {HorarioConfig.ENTRADA_SEMANA_HORA:02d}:{HorarioConfig.ENTRADA_SEMANA_MINUTO:02d}',
        max_instances=1,
        coalesce=True
    )
    logger.info(f"  ✓ Entrada L-V programada: {HorarioConfig.ENTRADA_SEMANA_HORA:02d}:{HorarioConfig.ENTRADA_SEMANA_MINUTO:02d}")
    
    # LUNES A VIERNES - SALIDA (horario base fijo, variación se aplica al ejecutar)
    scheduler.add_job(
        salida_semana,
        CronTrigger(
            day_of_week='mon-fri',
            hour=HorarioConfig.SALIDA_SEMANA_HORA,
            minute=HorarioConfig.SALIDA_SEMANA_MINUTO,
            timezone='America/Bogota'
        ),
        id='salida_semana',
        name=f'Salida L-V {HorarioConfig.SALIDA_SEMANA_HORA:02d}:{HorarioConfig.SALIDA_SEMANA_MINUTO:02d}',
        max_instances=1,
        coalesce=True
    )
    logger.info(f"  ✓ Salida L-V programada: {HorarioConfig.SALIDA_SEMANA_HORA:02d}:{HorarioConfig.SALIDA_SEMANA_MINUTO:02d}")
    
    # SÁBADOS - ENTRADA (horario base fijo, variación se aplica al ejecutar)
    scheduler.add_job(
        entrada_sabado,
        CronTrigger(
            day_of_week='sat',
            hour=HorarioConfig.ENTRADA_SABADO_HORA,
            minute=HorarioConfig.ENTRADA_SABADO_MINUTO,
            timezone='America/Bogota'
        ),
        id='entrada_sabado',
        name=f'Entrada Sábado {HorarioConfig.ENTRADA_SABADO_HORA:02d}:{HorarioConfig.ENTRADA_SABADO_MINUTO:02d}',
        max_instances=1,
        coalesce=True
    )
    logger.info(f"  ✓ Entrada Sábado programada: {HorarioConfig.ENTRADA_SABADO_HORA:02d}:{HorarioConfig.ENTRADA_SABADO_MINUTO:02d}")
    
    # SÁBADOS - SALIDA (horario base fijo, variación se aplica al ejecutar)
    scheduler.add_job(
        salida_sabado,
        CronTrigger(
            day_of_week='sat',
            hour=HorarioConfig.SALIDA_SABADO_HORA,
            minute=HorarioConfig.SALIDA_SABADO_MINUTO,
            timezone='America/Bogota'
        ),
        id='salida_sabado',
        name=f'Salida Sábado {HorarioConfig.SALIDA_SABADO_HORA:02d}:{HorarioConfig.SALIDA_SABADO_MINUTO:02d}',
        max_instances=1,
        coalesce=True
    )
    logger.info(f"  ✓ Salida Sábado programada: {HorarioConfig.SALIDA_SABADO_HORA:02d}:{HorarioConfig.SALIDA_SABADO_MINUTO:02d}")
    
    # VERIFICACIÓN PERIÓDICA cada hora
    scheduler.add_job(
        verificar_marcajes_pendientes,
        CronTrigger(
            minute=0,  # En punto cada hora
            timezone='America/Bogota'
        ),
        id='verificacion_periodica',
        name='Verificación periódica (cada hora)',
        max_instances=1,
        coalesce=True
    )
    logger.info(f"  ✓ Verificación periódica: Cada hora en punto")
    
    logger.info("=" * 80)
    logger.info("💡 Nota: La variación aleatoria se aplica al momento de ejecutar cada marcaje")

# Variable global para el scheduler
scheduler_global = None

def main():
    """Función principal del programador"""
    global scheduler_global
    
    logger.info("\n" + "=" * 80)
    logger.info("🚀 INICIANDO PROGRAMADOR DE MARCAJES GEOVICTORIA")
    logger.info("📍 Configurado para Colombia (incluye manejo de festivos)")
    logger.info(f"💻 Ejecutado desde: {Path(__file__).parent.parent}")
    logger.info(f"⏰ Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Mostrar festivos del año actual
    año_actual = datetime.now().year
    listar_festivos_año(año_actual)
    
    # Verificar si hay marcajes pendientes (PC iniciado tarde)
    logger.info("\n🔍 Verificando marcajes pendientes del día...")
    verificar_marcajes_pendientes()
    
    # Crear scheduler
    scheduler = BlockingScheduler(timezone='America/Bogota')
    scheduler_global = scheduler
    
    # Agregar listener para eventos
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    # Configurar trabajos con horarios fijos
    configurar_trabajos_fijos(scheduler)
    
    # Mostrar trabajos programados
    logger.info("\n📋 TRABAJOS PROGRAMADOS:")
    logger.info("=" * 80)
    for job in scheduler.get_jobs():
        try:
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else 'N/A'
        except AttributeError:
            next_run = 'Información no disponible'
        logger.info(f"  ✓ {job.name:25} | Próxima ejecución: {next_run}")
    logger.info("=" * 80)
    
    # Información sobre días excluidos
    logger.info("\n📌 CONFIGURACIÓN:")
    logger.info("  • Domingos: EXCLUIDOS (no se ejecuta)")
    logger.info("  • Festivos Colombia: EXCLUIDOS (validación automática)")
    logger.info("  • Zona horaria: America/Bogota")
    logger.info("  • Horarios base: FIJOS (variación aleatoria se aplica al ejecutar)")
    logger.info(f"    - Entrada L-V: {HorarioConfig.ENTRADA_SEMANA_HORA:02d}:{HorarioConfig.ENTRADA_SEMANA_MINUTO:02d} (± {HorarioConfig.VARIACION_ENTRADA_MIN} a {HorarioConfig.VARIACION_ENTRADA_MAX} min)")
    logger.info(f"    - Salida L-V: {HorarioConfig.SALIDA_SEMANA_HORA:02d}:{HorarioConfig.SALIDA_SEMANA_MINUTO:02d} (± {HorarioConfig.VARIACION_SALIDA_MIN} a {HorarioConfig.VARIACION_SALIDA_MAX} min)")
    logger.info(f"    - Entrada Sáb: {HorarioConfig.ENTRADA_SABADO_HORA:02d}:{HorarioConfig.ENTRADA_SABADO_MINUTO:02d} (± {HorarioConfig.VARIACION_ENTRADA_MIN} a {HorarioConfig.VARIACION_ENTRADA_MAX} min)")
    logger.info(f"    - Salida Sáb: {HorarioConfig.SALIDA_SABADO_HORA:02d}:{HorarioConfig.SALIDA_SABADO_MINUTO:02d} (± {HorarioConfig.VARIACION_SALIDA_MIN} a {HorarioConfig.VARIACION_SALIDA_MAX} min)")
    logger.info("  • Verificación periódica: CADA HORA (detecta y ejecuta marcajes pendientes)")
    logger.info("  • Recuperación automática: SI (al inicio y cada hora)")
    logger.info("=" * 80)
    
    logger.info("\n⏰ Programador activo. Presione Ctrl+C para detener.\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n👋 Programador detenido por el usuario")
        logger.info("=" * 80)

if __name__ == "__main__":
    main()
