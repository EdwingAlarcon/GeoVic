"""
Script para limpiar el registro de ejecuciones de hoy.
Soporta modo single (.env) y multi-empleado (employees.json).
"""
import json
import sys
from datetime import date
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "src" / "logs"


def obtener_archivos_registro() -> list:
    """Devuelve todos los archivos de registro existentes."""
    archivos = []
    default = LOG_DIR / "registro_ejecuciones.json"
    if default.exists():
        archivos.append(default)
    archivos += sorted(LOG_DIR.glob("registro_*.json"))
    return list(dict.fromkeys(archivos))  # sin duplicados, orden estable


def limpiar_registro_hoy():
    hoy = date.today().isoformat()
    archivos = obtener_archivos_registro()

    if not archivos:
        print("  No hay archivos de registro.")
        return

    limpiados = 0
    for archivo in archivos:
        try:
            data = json.loads(archivo.read_text(encoding="utf-8"))
            if hoy in data:
                emp_id = archivo.stem.replace("registro_", "").replace("ejecuciones", "default")
                print(f"\n  Empleado: {emp_id} ({archivo.name})")
                for tipo, datos in data[hoy].items():
                    print(f"    - {tipo}: {datos.get('hora', 'N/A')}")
                del data[hoy]
                archivo.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                print(f"    OK registro de {hoy} eliminado")
                limpiados += 1
            else:
                print(f"  Sin registro de hoy en {archivo.name}")
        except Exception as e:
            print(f"  Error procesando {archivo.name}: {e}")

    if limpiados > 0:
        print(f"\n  {limpiados} archivo(s) limpiado(s)")
        print("  Los marcajes se ejecutaran normalmente en sus horarios")
    else:
        print(f"\n  No habia registros de hoy que limpiar")


if __name__ == "__main__":
    print("=" * 60)
    print("  LIMPIAR REGISTRO DE EJECUCIONES DE HOY")
    print("=" * 60)
    print()

    auto = len(sys.argv) > 1 and sys.argv[1] == "--auto"
    if not auto:
        respuesta = input("Desea eliminar el registro de hoy de TODOS los empleados? (s/N): ")
        if respuesta.strip().lower() not in ("s", "si", "sí", "y", "yes"):
            print("Operacion cancelada")
            input("\nPresione Enter para salir...")
            sys.exit(0)

    limpiar_registro_hoy()

    if not auto:
        print()
        input("Presione Enter para salir...")
