"""
Script de emergencia para marcar salida cuando el programador falló
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.geovictoria import run, verificar_estado
from src.programador import guardar_registro
from datetime import date, datetime

async def marcar_salida_emergencia():
    """Marca salida de emergencia verificando primero el estado"""
    print("=" * 80)
    print("🚨 MARCAJE DE EMERGENCIA - SALIDA")
    print(f"📅 Fecha: {date.today().strftime('%A, %d de %B de %Y')}")
    print(f"🕐 Hora: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)
    
    # Verificar estado actual
    print("\n🔍 Verificando estado actual en GeoVictoria...")
    try:
        boton_disponible = await verificar_estado()
        print(f"✅ Botón disponible: Marcar {boton_disponible}")
        
        if boton_disponible == "Entrada":
            print("\n❌ ERROR: Se requiere marcar ENTRADA primero")
            print("   • No se puede marcar salida sin entrada previa")
            print("   • Por favor, marque entrada manualmente en GeoVictoria")
            return False
        
        # Ejecutar marcaje de salida
        print("\n📍 Ejecutando marcaje de SALIDA...")
        accion_ejecutada = await run(accion_esperada="Salida")
        
        if accion_ejecutada:
            print(f"\n✅ MARCAJE COMPLETADO: {accion_ejecutada}")
            
            # Determinar tipo según día
            dia_semana = date.today().weekday()
            if dia_semana == 5:
                tipo_marcaje = "SALIDA SÁBADO"
            else:
                tipo_marcaje = "SALIDA SEMANA (L-V)"
            
            # Registrar en el sistema (empleado por defecto = .env)
            print(f"💾 Registrando en sistema: {tipo_marcaje}")
            guardar_registro("default", tipo_marcaje, variacion_minutos=0)
            
            print("\n" + "=" * 80)
            print("✅ PROCESO COMPLETADO EXITOSAMENTE")
            print("=" * 80)
            return True
        else:
            print("\n❌ No se pudo completar el marcaje")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    resultado = asyncio.run(marcar_salida_emergencia())
    sys.exit(0 if resultado else 1)
