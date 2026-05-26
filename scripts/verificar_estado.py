#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar el estado de ejecuciones de marcaje.
Soporta modo single (.env) y multi-empleado (employees.json).
"""
import json
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LOG_DIR  = BASE_DIR / "src" / "logs"


def leer_todos_los_registros() -> dict:
    """
    Lee registros de TODOS los empleados.
    Devuelve {emp_id: registro_dict}.
    """
    resultados = {}

    # Registro del empleado por defecto (modo .env)
    default = LOG_DIR / "registro_ejecuciones.json"
    if default.exists():
        try:
            resultados["default"] = json.loads(default.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  Advertencia leyendo {default.name}: {e}")

    # Registros de empleados adicionales (modo employees.json)
    for archivo in sorted(LOG_DIR.glob("registro_*.json")):
        emp_id = archivo.stem.replace("registro_", "")
        if emp_id not in resultados:
            try:
                resultados[emp_id] = json.loads(archivo.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  Advertencia leyendo {archivo.name}: {e}")

    return resultados


def mostrar_estado_hoy():
    hoy = str(date.today())
    registros = leer_todos_los_registros()

    print(f"\n{'=' * 80}")
    print(f"ESTADO DE MARCAJES GEOVICTORIA")
    print(f"{'=' * 80}")
    print(f"\nFecha: {date.today().strftime('%A, %d de %B de %Y')}")
    print(f"Hora:  {datetime.now().strftime('%H:%M:%S')}")

    if not registros:
        print("\n  No hay archivos de registro (primer uso del sistema)")
        return

    total_hoy = 0
    for emp_id, registro in registros.items():
        marcajes_hoy = registro.get(hoy, {})
        if marcajes_hoy:
            print(f"\n  Empleado: {emp_id}")
            print(f"  {'-' * 60}")
            for tipo, datos in marcajes_hoy.items():
                hora = datetime.fromisoformat(datos["hora"]).strftime("%H:%M:%S")
                variacion = datos.get("variacion_minutos", 0)
                var_str = f"  (variacion {variacion:+d} min)" if variacion else ""
                print(f"    OK  {tipo}")
                print(f"        Hora: {hora}{var_str}")
            total_hoy += len(marcajes_hoy)

    if total_hoy == 0:
        print("\n  No hay marcajes registrados para hoy")
        print("  Posibles razones:")
        print("    - El programador no se ha ejecutado aun")
        print("    - Es dia festivo o domingo")
        print("    - Aun no es la hora programada")

    print(f"\n{'=' * 80}")


def mostrar_ultimos_dias(dias: int = 5):
    registros = leer_todos_los_registros()
    if not registros:
        return

    print(f"\nHISTORIAL ULTIMOS {dias} DIAS:")
    print(f"{'-' * 80}")

    for emp_id, registro in registros.items():
        fechas = sorted(registro.keys(), reverse=True)[:dias]
        if not fechas:
            continue
        print(f"\n  Empleado: {emp_id}")
        for fecha in fechas:
            try:
                fecha_obj = datetime.fromisoformat(fecha).date()
            except ValueError:
                fecha_obj = fecha
            print(f"    {fecha_obj}:")
            for tipo, datos in registro[fecha].items():
                hora = datetime.fromisoformat(datos["hora"]).strftime("%H:%M")
                print(f"      - {tipo}: {hora}")

    print(f"\n{'-' * 80}")


def verificar_logs_hoy():
    fecha_log = datetime.now().strftime("%Y%m%d")
    programador_log = LOG_DIR / f"programador_{fecha_log}.log"
    geovictoria_log = LOG_DIR / f"geovictoria_{fecha_log}.log"
    alerta_log      = LOG_DIR / "alertas.log"

    print(f"\nARCHIVOS DE LOG:")
    print(f"{'-' * 80}")

    for log in (programador_log, geovictoria_log):
        if log.exists():
            size = log.stat().st_size
            print(f"  OK  {log.name} ({size:,} bytes)")
            with open(log, "r", encoding="utf-8") as f:
                lineas = f.readlines()
            errores  = [l for l in lineas if "ERROR" in l or "Error" in l]
            marcajes = [l for l in lineas if "Marcaje completado" in l or "EXITOSO" in l]
            if errores:
                print(f"       {len(errores)} error(es) en el log")
            if marcajes:
                print(f"       {len(marcajes)} marcaje(s) completado(s)")
        else:
            print(f"  --  {log.name} (no existe aun hoy)")

    if alerta_log.exists():
        size = alerta_log.stat().st_size
        print(f"\n  ALERTAS: {alerta_log.name} ({size:,} bytes)")
        lineas = alerta_log.read_text(encoding="utf-8").splitlines()
        for l in lineas[-5:]:
            print(f"    {l}")
    else:
        print(f"\n  Sin alertas registradas")

    print(f"{'-' * 80}")


def main():
    print("\nVERIFICADOR DE ESTADO DE MARCAJES")
    mostrar_estado_hoy()
    mostrar_ultimos_dias(5)
    verificar_logs_hoy()
    print("\nVerificacion completada\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nVerificacion cancelada")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
