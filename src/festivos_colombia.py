"""
Módulo para gestionar festivos en Colombia
Incluye festivos fijos y móviles según la ley colombiana
"""
from datetime import datetime, date
from typing import List

def calcular_pascua(año: int) -> date:
    """Calcula la fecha de Pascua usando el algoritmo de Meeus/Jones/Butcher"""
    a = año % 19
    b = año // 100
    c = año % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(año, mes, dia)

def siguiente_lunes(fecha: date) -> date:
    """Mueve una fecha al siguiente lunes (Ley Emiliani)"""
    dias_hasta_lunes = (7 - fecha.weekday()) % 7
    if dias_hasta_lunes == 0:
        return fecha
    from datetime import timedelta
    return fecha + timedelta(days=dias_hasta_lunes)

def obtener_festivos_colombia(año: int) -> List[date]:
    """
    Retorna lista de festivos en Colombia para el año especificado
    Incluye festivos fijos y móviles según la legislación colombiana
    """
    festivos = []
    
    # Festivos fijos (no se mueven)
    festivos_fijos = [
        date(año, 1, 1),   # Año Nuevo
        date(año, 5, 1),   # Día del Trabajo
        date(año, 7, 20),  # Día de la Independencia
        date(año, 8, 7),   # Batalla de Boyacá
        date(año, 12, 8),  # Inmaculada Concepción
        date(año, 12, 25), # Navidad
    ]
    festivos.extend(festivos_fijos)
    
    # Festivos que se mueven al siguiente lunes (Ley Emiliani)
    festivos_movibles = [
        date(año, 1, 6),   # Reyes Magos
        date(año, 3, 19),  # San José
        date(año, 6, 29),  # San Pedro y San Pablo
        date(año, 8, 15),  # Asunción de la Virgen
        date(año, 10, 12), # Día de la Raza
        date(año, 11, 1),  # Todos los Santos
        date(año, 11, 11), # Independencia de Cartagena
    ]
    
    for festivo in festivos_movibles:
        festivos.append(siguiente_lunes(festivo))
    
    # Festivos basados en Pascua
    pascua = calcular_pascua(año)
    from datetime import timedelta
    
    # Jueves y Viernes Santo (3 y 2 días antes de Pascua)
    festivos.append(pascua - timedelta(days=3))  # Jueves Santo
    festivos.append(pascua - timedelta(days=2))  # Viernes Santo
    
    # Ascensión del Señor (39 días después de Pascua, se mueve al siguiente lunes)
    ascension = pascua + timedelta(days=39)
    festivos.append(siguiente_lunes(ascension))
    
    # Corpus Christi (60 días después de Pascua, se mueve al siguiente lunes)
    corpus = pascua + timedelta(days=60)
    festivos.append(siguiente_lunes(corpus))
    
    # Sagrado Corazón (68 días después de Pascua, se mueve al siguiente lunes)
    sagrado_corazon = pascua + timedelta(days=68)
    festivos.append(siguiente_lunes(sagrado_corazon))
    
    return sorted(festivos)

def es_festivo(fecha: date) -> bool:
    """Verifica si una fecha es festivo en Colombia"""
    festivos = obtener_festivos_colombia(fecha.year)
    return fecha in festivos

def es_dia_laborable(fecha: date = None) -> bool:
    """
    Verifica si una fecha es día laborable (no es festivo ni domingo)
    Si no se proporciona fecha, usa la fecha actual
    """
    if fecha is None:
        fecha = date.today()
    
    # Domingo = 6
    if fecha.weekday() == 6:
        return False
    
    return not es_festivo(fecha)

def obtener_proximo_dia_laborable(fecha: date = None) -> date:
    """Retorna el próximo día laborable desde la fecha dada"""
    from datetime import timedelta
    if fecha is None:
        fecha = date.today()
    
    while not es_dia_laborable(fecha):
        fecha += timedelta(days=1)
    
    return fecha

def listar_festivos_año(año: int = None) -> None:
    """Imprime todos los festivos del año"""
    if año is None:
        año = datetime.now().year
    
    festivos = obtener_festivos_colombia(año)
    print(f"\n📅 Festivos en Colombia {año}:")
    print("=" * 60)
    
    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    for festivo in festivos:
        dia_semana = dias_semana[festivo.weekday()]
        print(f"{dia_semana:10} {festivo.day:2} de {meses[festivo.month]:10} - {festivo.strftime('%Y-%m-%d')}")
    
    print("=" * 60)
    print(f"Total: {len(festivos)} festivos\n")

if __name__ == "__main__":
    # Prueba del módulo
    hoy = date.today()
    print(f"Hoy es: {hoy}")
    print(f"¿Es festivo?: {es_festivo(hoy)}")
    print(f"¿Es día laborable?: {es_dia_laborable(hoy)}")
    
    listar_festivos_año(2026)
