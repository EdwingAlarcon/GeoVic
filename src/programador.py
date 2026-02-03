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

from src.geovictoria import run
from src.festivos_colombia import es_dia_laborable, es_festivo, listar_festivos_año

# Configuración de logging y registro de ejecuciones
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"programador_{datetime.now().strftime('%Y%m%d')}.log"
registro_file = log_dir / "registro_ejecuciones.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

def ejecutar_marcaje_con_validacion(tipo_marcaje: str, variacion_minutos: int = 0):
    """
    Ejecutar marcaje solo si es día laborable (no festivo ni domingo)
    """
    hoy = date.today()
    
    logger.info("=" * 80)
    logger.info(f"🔔 Intento de marcaje programado: {tipo_marcaje}")
    logger.info(f"📅 Fecha: {hoy.strftime('%A, %d de %B de %Y')}")
    logger.info(f"🕐 Hora: {datetime.now().strftime('%H:%M:%S')}")
    if variacion_minutos != 0:
        logger.info(f"🎲 Variación aleatoria: {variacion_minutos:+d} minutos")
    
    # Verificar si es festivo
    if es_festivo(hoy):
        logger.warning(f"🎉 HOY ES FESTIVO - No se ejecutará el marcaje")
        logger.info("=" * 80)
        return
    
    # Verificar si es domingo
    if hoy.weekday() == 6:
        logger.warning(f"📅 HOY ES DOMINGO - No se ejecutará el marcaje")
        logger.info("=" * 80)
        return
    
    # Verificación adicional para sábados
    if hoy.weekday() == 5:
        logger.info(f"📅 Hoy es sábado - Horario especial activo")
    
    # Si llegamos aquí, es día laborable
    logger.info(f"✅ Día laborable confirmado - Ejecutando {tipo_marcaje}...")
    
    try:
        asyncio.run(run())
        logger.info(f"✅ {tipo_marcaje} completado exitosamente")
        # Registrar la ejecución exitosa
        guardar_registro_ejecucion(tipo_marcaje, variacion_minutos)
    except Exception as e:
        logger.error(f"❌ Error ejecutando {tipo_marcaje}: {e}", exc_info=True)
    
    logger.info("=" * 80)

def entrada_semana():
    """Marcaje de entrada Lunes a Viernes"""
    ejecutar_marcaje_con_validacion("ENTRADA SEMANA (L-V)")

def salida_semana():
    """Marcaje de salida Lunes a Viernes"""
    ejecutar_marcaje_con_validacion("SALIDA SEMANA (L-V)")

def entrada_sabado():
    """Marcaje de entrada Sábados"""
    ejecutar_marcaje_con_validacion("ENTRADA SÁBADO")

def salida_sabado():
    """Marcaje de salida Sábados"""
    ejecutar_marcaje_con_validacion("SALIDA SÁBADO")

# Versiones con variación aleatoria
def entrada_semana_con_variacion(variacion_minutos):
    """Marcaje de entrada Lunes a Viernes con variación aleatoria"""
    ejecutar_marcaje_con_validacion("ENTRADA SEMANA (L-V)", variacion_minutos)

def salida_semana_con_variacion(variacion_minutos):
    """Marcaje de salida Lunes a Viernes con variación aleatoria"""
    ejecutar_marcaje_con_validacion("SALIDA SEMANA (L-V)", variacion_minutos)

def entrada_sabado_con_variacion(variacion_minutos):
    """Marcaje de entrada Sábados con variación aleatoria"""
    ejecutar_marcaje_con_validacion("ENTRADA SÁBADO", variacion_minutos)

def salida_sabado_con_variacion(variacion_minutos):
    """Marcaje de salida Sábados con variación aleatoria"""
    ejecutar_marcaje_con_validacion("SALIDA SÁBADO", variacion_minutos)

def verificar_marcajes_pendientes():
    """Verifica y ejecuta marcajes pendientes si el PC se inició tarde"""
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
    
    # Verificar entrada pendiente
    if hora_actual > hora_entrada:
        if not ya_se_ejecuto_hoy(tipo_entrada):
            logger.warning(f"⚠️ MARCAJE PENDIENTE DETECTADO: {tipo_entrada}")
            logger.info(f"   • Hora programada: {hora_entrada.strftime('%H:%M')}")
            logger.info(f"   • Hora actual: {hora_actual.strftime('%H:%M')}")
            logger.info(f"   • El PC probablemente se inició tarde")
            logger.info("   • Ejecutando marcaje pendiente...")
            logger.info("=" * 80)
            
            ejecutar_marcaje_con_validacion(tipo_entrada)
            marcajes_ejecutados += 1
        else:
            logger.info(f"✅ {tipo_entrada} ya fue ejecutado hoy")
    else:
        logger.info(f"⏰ Aún no es hora de marcar entrada (programado: {hora_entrada.strftime('%H:%M')})")
    
    # Verificar salida pendiente
    if hora_actual > hora_salida:
        if not ya_se_ejecuto_hoy(tipo_salida):
            logger.warning(f"⚠️ MARCAJE PENDIENTE DETECTADO: {tipo_salida}")
            logger.info(f"   • Hora programada: {hora_salida.strftime('%H:%M')}")
            logger.info(f"   • Hora actual: {hora_actual.strftime('%H:%M')}")
            logger.info(f"   • El PC probablemente se inició tarde")
            logger.info("   • Ejecutando marcaje pendiente...")
            logger.info("=" * 80)
            
            ejecutar_marcaje_con_validacion(tipo_salida)
            marcajes_ejecutados += 1
        else:
            logger.info(f"✅ {tipo_salida} ya fue ejecutado hoy")
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

def main():
    """Función principal del programador"""
    logger.info("\n" + "=" * 80)
    logger.info("🚀 INICIANDO PROGRAMADOR DE MARCAJES GEOVICTORIA")
    logger.info("📍 Configurado para Colombia (incluye manejo de festivos)")
    logger.info("=" * 80)
    
    # Mostrar festivos del año actual
    año_actual = datetime.now().year
    listar_festivos_año(año_actual)
    
    # Verificar si hay marcajes pendientes (PC iniciado tarde)
    verificar_marcajes_pendientes()
    
    # Crear scheduler
    scheduler = BlockingScheduler(timezone='America/Bogota')
    
    # Agregar listener para eventos
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    # Configurar trabajos programados con horarios aleatorios
    logger.info("\n🎲 CALCULANDO HORARIOS ALEATORIOS PARA HOY:")
    logger.info("=" * 80)
    
    # LUNES A VIERNES - ENTRADA con variación aleatoria
    entrada_semana_time, var_entrada_semana = calcular_horario_aleatorio(
        HorarioConfig.ENTRADA_SEMANA_HORA,
        HorarioConfig.ENTRADA_SEMANA_MINUTO,
        HorarioConfig.VARIACION_ENTRADA_MIN,
        HorarioConfig.VARIACION_ENTRADA_MAX
    )
    scheduler.add_job(
        lambda: entrada_semana_con_variacion(var_entrada_semana),
        CronTrigger(
            day_of_week='mon-fri',
            hour=entrada_semana_time.hour,
            minute=entrada_semana_time.minute,
            timezone='America/Bogota'
        ),
        id='entrada_semana',
        name=f'Entrada L-V {entrada_semana_time.strftime("%H:%M")}',
        max_instances=1,
        coalesce=True
    )
    logger.info("")
    
    # LUNES A VIERNES - SALIDA con variación aleatoria
    salida_semana_time, var_salida_semana = calcular_horario_aleatorio(
        HorarioConfig.SALIDA_SEMANA_HORA,
        HorarioConfig.SALIDA_SEMANA_MINUTO,
        HorarioConfig.VARIACION_SALIDA_MIN,
        HorarioConfig.VARIACION_SALIDA_MAX
    )
    scheduler.add_job(
        lambda: salida_semana_con_variacion(var_salida_semana),
        CronTrigger(
            day_of_week='mon-fri',
            hour=salida_semana_time.hour,
            minute=salida_semana_time.minute,
            timezone='America/Bogota'
        ),
        id='salida_semana',
        name=f'Salida L-V {salida_semana_time.strftime("%H:%M")}',
        max_instances=1,
        coalesce=True
    )
    logger.info("")
    
    # SÁBADOS - ENTRADA con variación aleatoria
    entrada_sabado_time, var_entrada_sabado = calcular_horario_aleatorio(
        HorarioConfig.ENTRADA_SABADO_HORA,
        HorarioConfig.ENTRADA_SABADO_MINUTO,
        HorarioConfig.VARIACION_ENTRADA_MIN,
        HorarioConfig.VARIACION_ENTRADA_MAX
    )
    scheduler.add_job(
        lambda: entrada_sabado_con_variacion(var_entrada_sabado),
        CronTrigger(
            day_of_week='sat',
            hour=entrada_sabado_time.hour,
            minute=entrada_sabado_time.minute,
            timezone='America/Bogota'
        ),
        id='entrada_sabado',
        name=f'Entrada Sábado {entrada_sabado_time.strftime("%H:%M")}',
        max_instances=1,
        coalesce=True
    )
    logger.info("")
    
    # SÁBADOS - SALIDA con variación aleatoria
    salida_sabado_time, var_salida_sabado = calcular_horario_aleatorio(
        HorarioConfig.SALIDA_SABADO_HORA,
        HorarioConfig.SALIDA_SABADO_MINUTO,
        HorarioConfig.VARIACION_SALIDA_MIN,
        HorarioConfig.VARIACION_SALIDA_MAX
    )
    scheduler.add_job(
        lambda: salida_sabado_con_variacion(var_salida_sabado),
        CronTrigger(
            day_of_week='sat',
            hour=salida_sabado_time.hour,
            minute=salida_sabado_time.minute,
            timezone='America/Bogota'
        ),
        id='salida_sabado',
        name=f'Salida Sábado {salida_sabado_time.strftime("%H:%M")}',
        max_instances=1,
        coalesce=True
    )
    logger.info("=" * 80)
    
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
    logger.info("  • Horarios aleatorios: ACTIVADOS")
    logger.info(f"    - Entrada: {HorarioConfig.VARIACION_ENTRADA_MIN} a {HorarioConfig.VARIACION_ENTRADA_MAX} minutos")
    logger.info(f"    - Salida: {HorarioConfig.VARIACION_SALIDA_MIN} a {HorarioConfig.VARIACION_SALIDA_MAX} minutos")
    logger.info("  • Nota: Los horarios se recalculan cada día automáticamente")
    logger.info("=" * 80)
    
    logger.info("\n⏰ Programador activo. Presione Ctrl+C para detener.\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n👋 Programador detenido por el usuario")
        logger.info("=" * 80)

if __name__ == "__main__":
    main()
