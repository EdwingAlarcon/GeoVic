"""
Programador automático para marcaje de asistencia GeoVictoria
Configurado para Colombia con manejo de festivos
"""
import asyncio
import logging
import sys
import json
import random
import os
import atexit
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
lock_file = log_dir / "programador.lock"

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
    
    # Cooldown mínimo entre marcajes (segundos) - para prevenir marcajes consecutivos rápidos
    COOLDOWN_ENTRE_MARCAJES = 300  # 5 minutos

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
        ahora = datetime.now()
        ahora_iso = ahora.isoformat()
        
        if hoy not in registro:
            registro[hoy] = {}
        
        registro[hoy][tipo_marcaje] = {
            'ejecutado': True,
            'hora': ahora_iso,
            'timestamp': ahora.timestamp(),  # Para cálculos de tiempo
            'variacion_minutos': variacion_minutos
        }
        
        # Limpiar registros antiguos (mantener solo últimos 30 días)
        fechas = sorted(registro.keys(), reverse=True)
        if len(fechas) > 30:
            for fecha_antigua in fechas[30:]:
                del registro[fecha_antigua]
        
        with open(registro_file, 'w', encoding='utf-8') as f:
            json.dump(registro, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Registro guardado: {tipo_marcaje} a las {ahora_iso}")
    except Exception as e:
        logger.error(f"Error guardando registro de ejecución: {e}")

def ya_se_ejecuto_hoy(tipo_marcaje: str) -> bool:
    """Verifica si ya se ejecutó un tipo de marcaje hoy"""
    registro = leer_registro_ejecuciones()
    hoy = date.today().isoformat()
    
    if hoy in registro and tipo_marcaje in registro[hoy]:
        return registro[hoy][tipo_marcaje].get('ejecutado', False)
    
    return False

def tiempo_desde_ultimo_marcaje() -> float:
    """Retorna segundos desde el último marcaje de cualquier tipo (hoy)"""
    registro = leer_registro_ejecuciones()
    hoy = date.today().isoformat()
    
    if hoy not in registro:
        return float('inf')  # No hay marcajes hoy
    
    ahora = datetime.now().timestamp()
    timestamps = []
    
    for tipo_marcaje, info in registro[hoy].items():
        if 'timestamp' in info:
            timestamps.append(info['timestamp'])
    
    if not timestamps:
        return float('inf')
    
    ultimo_timestamp = max(timestamps)
    return ahora - ultimo_timestamp

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
    
    # PROTECCIÓN CRÍTICA: Verificar si ya se ejecutó (verificación temprana)
    if ya_se_ejecuto_hoy(tipo_marcaje):
        logger.warning(f"⏭️ {tipo_marcaje} YA FUE EJECUTADO HOY - OMITIENDO")
        logger.warning(f"   Esta es una protección contra ejecuciones duplicadas")
        logger.info("=" * 80)
        return None
    
    # PROTECCIÓN ADICIONAL: Cooldown entre marcajes
    segundos_desde_ultimo = tiempo_desde_ultimo_marcaje()
    if segundos_desde_ultimo < HorarioConfig.COOLDOWN_ENTRE_MARCAJES:
        tiempo_espera = HorarioConfig.COOLDOWN_ENTRE_MARCAJES - segundos_desde_ultimo
        logger.warning(f"⏸️ COOLDOWN ACTIVO")
        logger.warning(f"   • Último marcaje hace: {segundos_desde_ultimo:.0f} segundos")
        logger.warning(f"   • Cooldown mínimo: {HorarioConfig.COOLDOWN_ENTRE_MARCAJES} segundos")
        logger.warning(f"   • Tiempo restante: {tiempo_espera:.0f} segundos")
        logger.warning(f"   • NO se ejecutará {tipo_marcaje} para prevenir marcaje rápido consecutivo")
        logger.info("=" * 80)
        return None
    
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
    """Marcaje de entrada Lunes a Viernes SIN variación (horario fijo configurado en scheduler)"""
    # PROTECCIÓN: Verificar si ya se ejecutó antes de hacer nada
    if ya_se_ejecuto_hoy("ENTRADA SEMANA (L-V)"):
        logger.info("⏭️ ENTRADA SEMANA (L-V) ya ejecutada hoy - Omitiendo")
        return
    
    # No calcular variación - el scheduler ya programó en el horario exacto
    logger.info(f"📍 Ejecutando marcaje de entrada en horario programado")
    ejecutar_marcaje_con_validacion("ENTRADA SEMANA (L-V)", variacion_minutos=0)

def salida_semana():
    """Marcaje de salida Lunes a Viernes SIN variación (horario fijo configurado en scheduler)"""
    # PROTECCIÓN 1: Verificar si ya se ejecutó antes de hacer nada
    if ya_se_ejecuto_hoy("SALIDA SEMANA (L-V)"):
        logger.info("⏭️ SALIDA SEMANA (L-V) ya ejecutada hoy - Omitiendo")
        return
    
    # PROTECCIÓN 2: Verificar que existe entrada previa (orden lógico)
    if not ya_se_ejecuto_hoy("ENTRADA SEMANA (L-V)"):
        logger.warning("⚠️ SALIDA SEMANA (L-V) omitida - No hay entrada previa registrada")
        logger.warning("   • No se puede marcar salida sin haber marcado entrada primero")
        logger.warning("   • La verificación periódica intentará corregir esto más tarde")
        return
    
    # No calcular variación - el scheduler ya programó en el horario exacto
    logger.info(f"📍 Ejecutando marcaje de salida en horario programado")
    ejecutar_marcaje_con_validacion("SALIDA SEMANA (L-V)", variacion_minutos=0)

def entrada_sabado():
    """Marcaje de entrada Sábados SIN variación (horario fijo configurado en scheduler)"""
    # PROTECCIÓN: Verificar si ya se ejecutó antes de hacer nada
    if ya_se_ejecuto_hoy("ENTRADA SÁBADO"):
        logger.info("⏭️ ENTRADA SÁBADO ya ejecutada hoy - Omitiendo")
        return
    
    # No calcular variación - el scheduler ya programó en el horario exacto
    logger.info(f"📍 Ejecutando marcaje de entrada sábado en horario programado")
    ejecutar_marcaje_con_validacion("ENTRADA SÁBADO", variacion_minutos=0)

def salida_sabado():
    """Marcaje de salida Sábados SIN variación (horario fijo configurado en scheduler)"""
    # PROTECCIÓN 1: Verificar si ya se ejecutó antes de hacer nada
    if ya_se_ejecuto_hoy("SALIDA SÁBADO"):
        logger.info("⏭️ SALIDA SÁBADO ya ejecutada hoy - Omitiendo")
        return
    
    # PROTECCIÓN 2: Verificar que existe entrada previa (orden lógico)
    if not ya_se_ejecuto_hoy("ENTRADA SÁBADO"):
        logger.warning("⚠️ SALIDA SÁBADO omitida - No hay entrada previa registrada")
        logger.warning("   • No se puede marcar salida sin haber marcado entrada primero")
        logger.warning("   • La verificación periódica intentará corregir esto más tarde")
        return
    
    # No calcular variación - el scheduler ya programó en el horario exacto
    logger.info(f"📍 Ejecutando marcaje de salida sábado en horario programado")
    ejecutar_marcaje_con_validacion("SALIDA SÁBADO", variacion_minutos=0)

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
        else:
            # Validar que tenga sentido marcar entrada según la hora actual
            # No marcar entrada después de las 12 PM (mediodía)
            hora_limite_entrada = time(12, 0)
            
            if hora_actual > hora_limite_entrada:
                # Verificar si el usuario ya marcó entrada manualmente
                logger.info(f"⚠️ Pasó la hora límite de entrada (12:00 PM) - Verificando estado en GeoVictoria...")
                try:
                    boton_disponible = asyncio.run(verificar_estado())
                    if boton_disponible == "Salida":
                        # El usuario ya marcó entrada manualmente
                        logger.info(f"✅ {tipo_entrada} detectado en GeoVictoria (marcado manualmente)")
                        logger.info(f"   • Registrando entrada en sistema local...")
                        guardar_registro_ejecucion(tipo_entrada, variacion_minutos=0)
                        logger.info(f"💾 {tipo_entrada} registrado correctamente")
                    else:
                        logger.warning(f"⚠️ MARCAJE PERDIDO: {tipo_entrada}")
                        logger.warning(f"   • Demasiado tarde para marcar entrada automáticamente")
                        logger.warning(f"   • Por favor, marque entrada manualmente en GeoVictoria")
                except Exception as e:
                    logger.error(f"❌ Error verificando estado: {e}")
            else:
                logger.warning(f"⚠️ MARCAJE PENDIENTE DETECTADO: {tipo_entrada}")
                logger.info(f"   • Hora programada: {hora_entrada.strftime('%H:%M')}")
                logger.info(f"   • Hora actual: {hora_actual.strftime('%H:%M')}")
                
                # Primero verificar qué botón está disponible en GeoVictoria
                try:
                    boton_disponible = asyncio.run(verificar_estado())
                    if boton_disponible == "Salida":
                        # El usuario ya marcó entrada manualmente
                        logger.info(f"✅ {tipo_entrada} detectado en GeoVictoria (marcado manualmente)")
                        logger.info(f"   • Registrando entrada en sistema local...")
                        guardar_registro_ejecucion(tipo_entrada, variacion_minutos=0)
                        logger.info(f"💾 {tipo_entrada} registrado correctamente")
                    elif boton_disponible == "Entrada":
                        logger.info("   • El PC probablemente se inició tarde")
                        logger.info("   • Ejecutando marcaje pendiente...")
                        logger.info("=" * 80)
                        # NO validar horario en marcajes pendientes
                        ejecutar_marcaje_con_validacion(tipo_entrada, validar_horario=False)
                        marcajes_ejecutados += 1
                    else:
                        logger.warning(f"⚠️ No se pudo determinar el estado en GeoVictoria")
                except Exception as e:
                    logger.error(f"❌ Error verificando estado: {e}")
    else:
        logger.info(f"⏰ Aún no es hora de marcar entrada (programado: {hora_entrada.strftime('%H:%M')})")
    
    # Verificar salida pendiente
    if hora_actual > hora_salida:
        if not ya_se_ejecuto_hoy(tipo_salida):
            # Validar que la entrada ya se haya marcado
            if not ya_se_ejecuto_hoy(tipo_entrada):
                logger.warning(f"⚠️ MARCAJE PENDIENTE OMITIDO: {tipo_salida}")
                logger.warning(f"   • No se puede marcar salida sin entrada previa registrada")
                logger.warning(f"   • Verificando estado en GeoVictoria...")
                try:
                    boton_disponible = asyncio.run(verificar_estado())
                    if boton_disponible == "Salida":
                        # Hay entrada marcada pero no registrada localmente
                        logger.info(f"✅ Se detectó entrada previa en GeoVictoria")
                        logger.info(f"   • Registrando entrada en sistema local...")
                        guardar_registro_ejecucion(tipo_entrada, variacion_minutos=0)
                        logger.info(f"💾 {tipo_entrada} registrado correctamente")
                        logger.info(f"   • Ahora verificando marcaje de salida pendiente...")
                        # Continuar con la verificación de salida
                        hora_limite_salida = time(23, 0)
                        if hora_actual > hora_limite_salida:
                            logger.warning(f"⚠️ MARCAJE PENDIENTE OMITIDO: {tipo_salida}")
                            logger.warning(f"   • Demasiado tarde para marcar salida (después de 11:00 PM)")
                        else:
                            logger.warning(f"⚠️ MARCAJE PENDIENTE DETECTADO: {tipo_salida}")
                            logger.info(f"   • Ejecutando marcaje pendiente...")
                            logger.info("=" * 80)
                            ejecutar_marcaje_con_validacion(tipo_salida, validar_horario=False)
                            marcajes_ejecutados += 1
                    else:
                        logger.warning(f"   • ACCIÓN: Debe marcar entrada primero")
                except Exception as e:
                    logger.error(f"❌ Error verificando estado: {e}")
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
    logger.info("💡 Nota: Los marcajes se ejecutan en horarios FIJOS (sin variación aleatoria)")

# Variable global para el scheduler
scheduler_global = None

def crear_lock_file():
    """Crea un archivo de lock para prevenir múltiples instancias"""
    if lock_file.exists():
        try:
            # Leer el PID del proceso existente
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Verificar si el proceso sigue corriendo
            try:
                import psutil
                if psutil.pid_exists(pid):
                    logger.error("=" * 80)
                    logger.error("❌ ERROR: El programador ya está ejecutándose")
                    logger.error(f"   PID del proceso existente: {pid}")
                    logger.error("   Por favor detenga la instancia anterior antes de iniciar una nueva")
                    logger.error("=" * 80)
                    sys.exit(1)
                else:
                    logger.warning(f"⚠️ Lock file obsoleto encontrado (PID {pid} no existe) - Recreando")
            except ImportError:
                # Si psutil no está disponible, verificar con método alternativo
                logger.warning("⚠️ psutil no disponible - Verificando lock file con método básico")
                # Intentar verificar si el archivo es muy antiguo (más de 1 día)
                from datetime import datetime
                lock_age = datetime.now().timestamp() - lock_file.stat().st_mtime
                if lock_age > 86400:  # 1 día
                    logger.warning(f"⚠️ Lock file tiene {lock_age/3600:.1f} horas - Recreando")
                else:
                    logger.error("=" * 80)
                    logger.error("❌ ERROR: Lock file existe y podría haber otra instancia corriendo")
                    logger.error(f"   PID en lock file: {pid}")
                    logger.error(f"   Si está seguro que no hay otra instancia, elimine: {lock_file}")
                    logger.error("=" * 80)
                    sys.exit(1)
        except Exception as e:
            logger.warning(f"⚠️ Error verificando lock file: {e} - Recreando")
    
    # Crear lock file con el PID actual
    with open(lock_file, 'w') as f:
        f.write(str(os.getpid()))
    logger.info(f"🔒 Lock file creado: PID {os.getpid()}")

def eliminar_lock_file():
    """Elimina el archivo de lock al salir"""
    try:
        if lock_file.exists():
            lock_file.unlink()
            logger.info("🔓 Lock file eliminado")
    except Exception as e:
        logger.error(f"Error eliminando lock file: {e}")

def main():
    """Función principal del programador"""
    global scheduler_global
    
    # PROTECCIÓN: Verificar si ya hay una instancia corriendo
    crear_lock_file()
    
    # Registrar limpieza del lock file al salir
    atexit.register(eliminar_lock_file)
    
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
    logger.info("  • Horarios: FIJOS (exactos, sin variación aleatoria)")
    logger.info(f"    - Entrada L-V: {HorarioConfig.ENTRADA_SEMANA_HORA:02d}:{HorarioConfig.ENTRADA_SEMANA_MINUTO:02d}")
    logger.info(f"    - Salida L-V: {HorarioConfig.SALIDA_SEMANA_HORA:02d}:{HorarioConfig.SALIDA_SEMANA_MINUTO:02d}")
    logger.info(f"    - Entrada Sáb: {HorarioConfig.ENTRADA_SABADO_HORA:02d}:{HorarioConfig.ENTRADA_SABADO_MINUTO:02d}")
    logger.info(f"    - Salida Sáb: {HorarioConfig.SALIDA_SABADO_HORA:02d}:{HorarioConfig.SALIDA_SABADO_MINUTO:02d}")
    logger.info(f"  • Cooldown entre marcajes: {HorarioConfig.COOLDOWN_ENTRE_MARCAJES} segundos")
    logger.info("  • Verificación periódica: CADA HORA (detecta y ejecuta marcajes pendientes)")
    logger.info("  • Recuperación automática: SI (al inicio y cada hora)")
    logger.info("  • Protección contra duplicados: MÚLTIPLES CAPAS (registro + cooldown + validación)")
    logger.info("=" * 80)
    
    logger.info("\n⏰ Programador activo. Presione Ctrl+C para detener.\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n👋 Programador detenido por el usuario")
        logger.info("=" * 80)

if __name__ == "__main__":
    main()
