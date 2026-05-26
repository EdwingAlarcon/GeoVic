"""
Script para verificar el estado actual del sistema de marcajes.
Soporta modo single (.env) y multi-empleado (employees.json).
"""
import sys
import json
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.programador import leer_registro, ya_se_ejecuto_hoy, verificar_pendientes_emp
from src.empleados import cargar_empleados


def main():
    print("=" * 80)
    print("DIAGNOSTICO DEL SISTEMA DE MARCAJES")
    print("=" * 80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Cargar empleados
    try:
        empleados = cargar_empleados()
    except ValueError as e:
        print(f"Error cargando empleados: {e}")
        sys.exit(1)

    print(f"Empleados activos: {len(empleados)}")
    for emp in empleados:
        print(f"  - [{emp['id']}] {emp['nombre']}")
    print()

    hoy = date.today()
    dia_semana = hoy.weekday()

    for emp in empleados:
        emp_id    = emp["id"]
        emp_nombre = emp["nombre"]
        print("=" * 80)
        print(f"REGISTRO: {emp_nombre}")
        print("-" * 80)

        registro = leer_registro(emp_id)

        if not registro:
            print("  Sin marcajes registrados aun")
        else:
            for fecha in sorted(registro.keys(), reverse=True)[:7]:
                print(f"\n  {fecha}:")
                for tipo, info in registro[fecha].items():
                    hora = info.get("hora", "N/A")
                    try:
                        hora_str = datetime.fromisoformat(hora).strftime("%H:%M:%S")
                    except Exception:
                        hora_str = str(hora)
                    variacion = info.get("variacion_minutos", 0)
                    var_str = f" (variacion {variacion:+d} min)" if variacion else ""
                    print(f"    OK {tipo}: {hora_str}{var_str}")

        # Estado de hoy
        print(f"\n  Estado de hoy:")
        if dia_semana == 5:
            tipo_entrada, tipo_salida = "ENTRADA SABADO", "SALIDA SABADO"
        elif dia_semana == 6:
            print("    Hoy es domingo - sin marcajes")
            continue
        else:
            tipo_entrada, tipo_salida = "ENTRADA SEMANA (L-V)", "SALIDA SEMANA (L-V)"

        entrada_ok = ya_se_ejecuto_hoy(emp_id, tipo_entrada)
        salida_ok  = ya_se_ejecuto_hoy(emp_id, tipo_salida)
        print(f"    Entrada: {'OK Registrada' if entrada_ok else 'PENDIENTE'} ({tipo_entrada})")
        print(f"    Salida:  {'OK Registrada' if salida_ok  else 'PENDIENTE'} ({tipo_salida})")

    print("\n" + "=" * 80)
    print("VERIFICANDO MARCAJES PENDIENTES...")
    print("=" * 80)

    for emp in empleados:
        verificar_pendientes_emp(emp)

    print("\n" + "=" * 80)
    print("DIAGNOSTICO COMPLETADO")
    print("=" * 80)


if __name__ == "__main__":
    main()
