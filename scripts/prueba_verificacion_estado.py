"""
Script de prueba para verificar el estado actual en GeoVictoria
y demostrar la nueva funcionalidad de detección de inconsistencias
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.geovictoria import verificar_estado
from src.programador import leer_registro_ejecuciones
from datetime import date

async def main():
    print("=" * 80)
    print("🔍 PRUEBA DE VERIFICACIÓN DE ESTADO")
    print("=" * 80)
    
    # Leer registro local
    print("\n📋 Registro local de hoy:")
    registro = leer_registro_ejecuciones()
    hoy = date.today().isoformat()
    
    if hoy in registro:
        for tipo, info in registro[hoy].items():
            print(f"   • {tipo}: ejecutado a las {info['hora']}")
    else:
        print("   • No hay registros para hoy")
    
    # Verificar estado real en GeoVictoria
    print("\n🌐 Consultando estado real en GeoVictoria...")
    print("   (Esto puede tardar unos segundos...)")
    
    boton_disponible = await verificar_estado()
    
    print("\n" + "=" * 80)
    print("📊 RESULTADO:")
    print("=" * 80)
    
    if boton_disponible:
        print(f"✅ Botón disponible en GeoVictoria: Marcar {boton_disponible}")
        
        # Verificar inconsistencias
        if hoy in registro:
            if boton_disponible == "Entrada" and "ENTRADA SEMANA (L-V)" in registro[hoy]:
                print("\n⚠️  INCONSISTENCIA DETECTADA:")
                print("   • Registro local indica: ENTRADA ya ejecutada")
                print("   • Estado real: Botón 'Marcar Entrada' disponible")
                print("   • Causa probable: Se registró una salida accidental")
                print("   • Acción sugerida: El sistema re-ejecutará automáticamente")
            elif boton_disponible == "Salida" and "SALIDA SEMANA (L-V)" in registro[hoy]:
                print("\n⚠️  INCONSISTENCIA DETECTADA:")
                print("   • Registro local indica: SALIDA ya ejecutada")
                print("   • Estado real: Botón 'Marcar Salida' disponible")
            else:
                print("\n✅ Registro local y estado real coinciden")
        else:
            print("\n💡 No hay registro local, pero GeoVictoria permite marcaje")
    else:
        print("❌ Ningún botón de marcaje disponible")
        print("   Esto puede significar:")
        print("   • No es horario de marcaje")
        print("   • Ya se realizaron entrada y salida")
        print("   • Hay un problema de conexión")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
