"""
Script para limpiar el registro de ejecuciones de hoy
Útil cuando se detectan marcajes incorrectos o duplicados
"""
import json
import sys
from datetime import date
from pathlib import Path

# Obtener la ruta del archivo de registro
script_dir = Path(__file__).parent.parent / "src" / "logs"
registro_file = script_dir / "registro_ejecuciones.json"

def limpiar_registro_hoy():
    """Elimina el registro del día de hoy del archivo JSON"""
    try:
        if not registro_file.exists():
            print("ℹ️  Archivo de registro no encontrado")
            return
        
        # Leer el registro actual
        with open(registro_file, 'r', encoding='utf-8') as f:
            registro = json.load(f)
        
        hoy = date.today().isoformat()
        
        if hoy in registro:
            print(f"📅 Limpiando registro de {hoy}...")
            print(f"   Marcajes a eliminar:")
            for tipo_marcaje, datos in registro[hoy].items():
                print(f"     • {tipo_marcaje}: {datos.get('hora', 'N/A')}")
            
            # Eliminar el registro de hoy
            del registro[hoy]
            
            # Guardar el registro actualizado
            with open(registro_file, 'w', encoding='utf-8') as f:
                json.dump(registro, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Registro de {hoy} eliminado exitosamente")
            print("⚠️  Los marcajes programados se ejecutarán normalmente en sus horarios")
        else:
            print(f"ℹ️  No hay registro para {hoy}")
    
    except Exception as e:
        print(f"❌ Error limpiando registro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("  LIMPIAR REGISTRO DE EJECUCIONES DE HOY")
    print("=" * 60)
    print()
    
    # Si se pasa --auto como argumento, no pedir confirmación
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        limpiar_registro_hoy()
    else:
        respuesta = input("¿Está seguro que desea eliminar el registro de hoy? (s/N): ")
        
        if respuesta.lower() in ['s', 'si', 'sí', 'y', 'yes']:
            limpiar_registro_hoy()
        else:
            print("❌ Operación cancelada")
        
        print()
        input("Presione Enter para salir...")
