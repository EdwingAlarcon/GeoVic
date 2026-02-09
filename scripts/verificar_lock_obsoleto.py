"""
Script para verificar y limpiar lock files obsoletos
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.programador import lock_file

def verificar_lock():
    """Verifica si el lock file está obsoleto y lo limpia si es necesario"""
    if not lock_file.exists():
        print("✅ No hay lock file - El programador puede iniciarse sin problemas")
        return True
    
    try:
        with open(lock_file, 'r') as f:
            pid = int(f.read().strip())
        
        print(f"📌 Lock file encontrado con PID: {pid}")
        
        # Verificar si el proceso existe
        try:
            import psutil
            if psutil.pid_exists(pid):
                print(f"⚠️  El proceso {pid} ESTÁ CORRIENDO")
                print(f"   Si está seguro que no hay otra instancia del programador,")
                print(f"   use el script 'detener_todas_instancias.bat' para detenerlo")
                return False
            else:
                print(f"🧹 El proceso {pid} NO EXISTE - Lock file obsoleto")
                lock_file.unlink()
                print(f"✅ Lock file eliminado correctamente")
                return True
        except ImportError:
            print("⚠️  psutil no disponible - No se puede verificar el proceso")
            print(f"   Elimine manualmente el archivo si está seguro: {lock_file}")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando lock file: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🔍 VERIFICANDO LOCK FILE DEL PROGRAMADOR")
    print("=" * 70)
    
    resultado = verificar_lock()
    
    print("=" * 70)
    
    sys.exit(0 if resultado else 1)
