#!/usr/bin/env python3
"""
Marca asistencia manualmente para todos los empleados activos.
BYPASA la ventana de tiempo — úsalo para recuperar marcajes perdidos.

Uso:
  python scripts/marcar_forzado.py               # auto-detecta entrada/salida por hora
  python scripts/marcar_forzado.py salida         # fuerza Salida para todos
  python scripts/marcar_forzado.py entrada        # fuerza Entrada para todos
  python scripts/marcar_forzado.py salida emp2    # fuerza Salida solo para emp2
"""
import asyncio
import json
import sys
from datetime import date, datetime, time
from pathlib import Path

# Agregar la raíz del repo al path para poder importar src.*
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.empleados import cargar_empleados
from src.geovictoria import run

LOG_DIR = REPO_ROOT / "src" / "logs"
LOG_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Registro local (espejo del que usa programador.py)
# ---------------------------------------------------------------------------

def _registro_path(emp_id: str) -> Path:
    if emp_id == "default":
        return LOG_DIR / "registro_ejecuciones.json"
    return LOG_DIR / f"registro_{emp_id}.json"


def guardar_registro(emp_id: str, tipo_marcaje: str) -> None:
    path = _registro_path(emp_id)
    try:
        registro = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                registro = json.load(f)

        hoy = date.today().isoformat()
        ahora = datetime.now()
        registro.setdefault(hoy, {})[tipo_marcaje] = {
            "ejecutado": True,
            "hora": ahora.isoformat(),
            "timestamp": ahora.timestamp(),
            "variacion_minutos": 0,
        }

        # Mantener solo los últimos 30 días
        for fecha in sorted(registro.keys(), reverse=True)[30:]:
            del registro[fecha]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(registro, f, indent=2, ensure_ascii=False)
        print(f"    💾 Registro guardado: {path.name}")
    except Exception as e:
        print(f"    ⚠️  Error guardando registro: {e}")


# ---------------------------------------------------------------------------
# Auto-detección de acción
# ---------------------------------------------------------------------------

def detectar_accion(empleado: dict) -> str:
    """Decide Entrada o Salida según la hora actual vs. horario del empleado."""
    ahora = datetime.now().time()
    h = empleado["horario"]
    hora_salida = time(h["salida_semana_hora"], h["salida_semana_minuto"])

    # Después de mediodía y pasada la mitad del turno → Salida
    if ahora >= hora_salida:
        return "Salida"
    if ahora >= time(12, 0):
        return "Salida"
    return "Entrada"


def tipo_marcaje(accion: str) -> str:
    dia = date.today().weekday()
    sufijo = " SÁBADO" if dia == 5 else " SEMANA (L-V)"
    return ("ENTRADA" if accion == "Entrada" else "SALIDA") + sufijo


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # --- Parsear argumentos ---
    accion_arg = sys.argv[1].strip().lower() if len(sys.argv) > 1 else None
    emp_filtro = sys.argv[2].strip() if len(sys.argv) > 2 else None

    if accion_arg and accion_arg not in ("entrada", "salida"):
        print(f"ERROR: accion invalida '{accion_arg}'. Usa 'entrada' o 'salida'.")
        sys.exit(1)

    accion_fija = accion_arg.capitalize() if accion_arg else None  # "Entrada" o "Salida"

    print("=" * 65)
    print("  MARCAJE FORZADO — GeoVictoria")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if accion_fija:
        print(f"  Accion fijada: {accion_fija}")
    else:
        print("  Accion: auto-detectada por hora")
    print("=" * 65)

    # --- Cargar empleados ---
    try:
        empleados = cargar_empleados()
    except ValueError as e:
        print(f"\nERROR cargando empleados: {e}")
        sys.exit(1)

    # --- Filtrar por empleado si se indicó ---
    if emp_filtro:
        empleados = [e for e in empleados if e["id"] == emp_filtro]
        if not empleados:
            ids_disponibles = ", ".join(
                e["id"] for e in cargar_empleados()
            )
            print(f"\nERROR: no existe empleado con id='{emp_filtro}'.")
            print(f"  IDs disponibles: {ids_disponibles}")
            sys.exit(1)

    resultados = []

    for emp in empleados:
        accion = accion_fija or detectar_accion(emp)
        tipo = tipo_marcaje(accion)

        print(f"\n👤 {emp['nombre']}  [{emp['id']}]")
        print(f"   → Accion: {accion}  (se guardara como '{tipo}')")

        try:
            resultado = asyncio.run(run(accion_esperada=accion, empleado=emp))

            if resultado:
                guardar_registro(emp["id"], tipo)
                print(f"   ✅ Exito: marcaje '{resultado}' ejecutado")
                resultados.append((emp["nombre"], accion, "OK"))
            else:
                print(f"   ❌ El portal no ejecuto el marcaje")
                print(f"      (puede que el boton no sea '{accion}' ahora mismo)")
                resultados.append((emp["nombre"], accion, "FALLO - boton incorrecto"))

        except Exception as e:
            print(f"   ❌ Error: {e}")
            resultados.append((emp["nombre"], accion, f"ERROR: {e}"))

    # --- Resumen ---
    print("\n" + "=" * 65)
    print("  RESUMEN:")
    for nombre, accion, estado in resultados:
        icono = "✅" if estado == "OK" else "❌"
        print(f"  {icono}  {nombre}: {accion} — {estado}")
    print("=" * 65)

    # Salir con código de error si alguno falló
    fallos = [r for r in resultados if r[2] != "OK"]
    if fallos:
        sys.exit(1)


if __name__ == "__main__":
    main()
