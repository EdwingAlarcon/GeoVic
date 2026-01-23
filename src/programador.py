"""
Programador automático para marcaje de asistencia GeoVictoria
Configurado para Colombia con manejo de festivos
"""
import asyncio
import logging
from datetime import datetime, date
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from pathlib import Path

from src.geovictoria import run
from src.festivos_colombia import es_dia_laborable, es_festivo, listar_festivos_año

# Configuración de logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"programador_{datetime.now().strftime('%Y%m%d')}.log"

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

def ejecutar_marcaje_con_validacion(tipo_marcaje: str):
    """
    Ejecutar marcaje solo si es día laborable (no festivo ni domingo)
    """
    hoy = date.today()
    
    logger.info("=" * 80)
    logger.info(f"🔔 Intento de marcaje programado: {tipo_marcaje}")
    logger.info(f"📅 Fecha: {hoy.strftime('%A, %d de %B de %Y')}")
    logger.info(f"🕐 Hora: {datetime.now().strftime('%H:%M:%S')}")
    
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
    
    # Crear scheduler
    scheduler = BlockingScheduler(timezone='America/Bogota')
    
    # Agregar listener para eventos
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    # Configurar trabajos programados
    
    # LUNES A VIERNES - ENTRADA 7:00 AM
    scheduler.add_job(
        entrada_semana,
        CronTrigger(
            day_of_week='mon-fri',
            hour=HorarioConfig.ENTRADA_SEMANA_HORA,
            minute=HorarioConfig.ENTRADA_SEMANA_MINUTO,
            timezone='America/Bogota'
        ),
        id='entrada_semana',
        name='Entrada L-V 7:00 AM',
        max_instances=1,
        coalesce=True
    )
    
    # LUNES A VIERNES - SALIDA 5:00 PM
    scheduler.add_job(
        salida_semana,
        CronTrigger(
            day_of_week='mon-fri',
            hour=HorarioConfig.SALIDA_SEMANA_HORA,
            minute=HorarioConfig.SALIDA_SEMANA_MINUTO,
            timezone='America/Bogota'
        ),
        id='salida_semana',
        name='Salida L-V 5:00 PM',
        max_instances=1,
        coalesce=True
    )
    
    # SÁBADOS - ENTRADA 7:00 AM
    scheduler.add_job(
        entrada_sabado,
        CronTrigger(
            day_of_week='sat',
            hour=HorarioConfig.ENTRADA_SABADO_HORA,
            minute=HorarioConfig.ENTRADA_SABADO_MINUTO,
            timezone='America/Bogota'
        ),
        id='entrada_sabado',
        name='Entrada Sábado 7:00 AM',
        max_instances=1,
        coalesce=True
    )
    
    # SÁBADOS - SALIDA 1:00 PM
    scheduler.add_job(
        salida_sabado,
        CronTrigger(
            day_of_week='sat',
            hour=HorarioConfig.SALIDA_SABADO_HORA,
            minute=HorarioConfig.SALIDA_SABADO_MINUTO,
            timezone='America/Bogota'
        ),
        id='salida_sabado',
        name='Salida Sábado 1:00 PM',
        max_instances=1,
        coalesce=True
    )
    
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
    logger.info("=" * 80)
    
    logger.info("\n⏰ Programador activo. Presione Ctrl+C para detener.\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n👋 Programador detenido por el usuario")
        logger.info("=" * 80)

if __name__ == "__main__":
    main()
