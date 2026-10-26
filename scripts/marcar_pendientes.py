#!/usr/bin/env python3
"""
Marca los pendientes indicados (EMPLEADO:accion), SOLO si el portal ofrece ese botón.

Uso:
  python scripts/marcar_pendientes.py emp4:salida emp2:salida
  python scripts/marcar_pendientes.py emp1:entrada

Es lo que ejecuta el botón "Marcar pendientes" del monitor. A diferencia de marcar_forzado.py:
  - recibe pares explícitos empleado:acción, nunca marca "a todos";
  - run() solo hace clic si el portal ofrece el botón de esa acción (un botón ofrecido significa que
    ese marcaje NO existe), así que no puede duplicar un marcaje ya hecho;
  - salta a quien tenga actividad reciente de otro proceso (el programador puede estar marcándolo);
  - confirma con un segundo login y deja eventos en la bitácora.

No imprime usuarios ni contraseñas.
"""
import asyncio
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import bitacora
from src.empleados import cargar_empleados
from src.estado_monitor import confirmacion_de
from src.festivos_colombia import es_festivo
from src.geovictoria import run, verificar_estado

OCUPADO_SEG = 90
_EVENTOS_DE_ACTIVIDAD = ("login", "marcaje", "confirmacion", "reintento", "marcaje_manual")


def parsear_pares(argumentos: List[str]) -> List[Tuple[str, str]]:
    """["emp4:salida"] -> [("emp4", "Salida")]. Lanza ValueError si un par no es válido."""
    pares = []
    for texto in argumentos:
        emp_id, _, accion = texto.partition(":")
        if not emp_id or accion.lower() not in ("entrada", "salida"):
            raise ValueError(f"Par no válido '{texto}': use EMPLEADO:entrada o EMPLEADO:salida")
        pares.append((emp_id, accion.capitalize()))
    return pares


def esta_ocupado(eventos: List[Dict], emp_id: str, ahora: datetime, mi_pid: int) -> bool:
    """True si otro proceso tuvo actividad con este empleado en los últimos OCUPADO_SEG segundos."""
    limite = (ahora - timedelta(seconds=OCUPADO_SEG)).isoformat(timespec="seconds")
    return any(e.get("emp_id") == emp_id and e.get("pid") != mi_pid and e.get("tipo") in _EVENTOS_DE_ACTIVIDAD
               and str(e.get("ts", "")) >= limite for e in eventos)


def tipo_marcaje(accion: str, dia: date) -> str:
    sufijo = "SÁBADO" if dia.weekday() == 5 else "SEMANA (L-V)"
    return f"{accion.upper()} {sufijo}"


def _ruta_registro(emp_id: str) -> Path:
    return bitacora.LOG_DIR / ("registro_ejecuciones.json" if emp_id == "default" else f"registro_{emp_id}.json")


def guardar_registro(emp_id: str, tipo: str, origen: str, ejecutado: bool = True) -> None:
    ruta = _ruta_registro(emp_id)
    try:
        registro = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    except ValueError:
        registro = {}
    ahora = datetime.now()
    registro.setdefault(date.today().isoformat(), {})[tipo] = {
        "ejecutado": ejecutado, "hora": ahora.isoformat(), "timestamp": ahora.timestamp(),
        "variacion_minutos": 0, "origen": origen,
    }
    for fecha in sorted(registro.keys(), reverse=True)[30:]:
        del registro[fecha]
    bitacora.escribir_json_atomico(ruta, registro)


def marcar(emp: Dict, accion: str) -> str:
    """Intenta marcar una acción. Devuelve una línea de resumen para mostrar."""
    nombre, emp_id = emp["nombre"], emp["id"]
    tipo = tipo_marcaje(accion, date.today())
    resultado = asyncio.run(run(accion_esperada=accion, empleado=emp))
    bitacora.registrar("marcaje_manual", emp, accion=accion, resultado="ok" if resultado else "no_realizado")

    if resultado:
        guardar_registro(emp_id, tipo, "manual")
        boton = asyncio.run(verificar_estado(empleado=emp))
        confirmada = confirmacion_de(accion, boton)
        bitacora.registrar("confirmacion", emp, accion=accion, tipo_marcaje=tipo, confirmada=confirmada,
                           boton=boton, intento=1, via="marcaje_manual")
        if confirmada is False:
            guardar_registro(emp_id, tipo, "manual", ejecutado=False)
            return f"✖ {nombre}: {accion} NO quedó en el portal (sigue ofreciendo '{boton}')"
        if confirmada:
            return f"✔ {nombre}: {accion} marcada y confirmada"
        return f"✔ {nombre}: {accion} marcada (sin confirmación concluyente)"

    boton = asyncio.run(verificar_estado(empleado=emp))
    if confirmacion_de(accion, boton) is True:
        guardar_registro(emp_id, tipo, "portal")
        return f"ℹ {nombre}: {accion} ya estaba registrada en el portal (no se hizo clic)"
    return f"✖ {nombre}: no se pudo marcar {accion} (el portal ofrece '{boton or 'ningún botón'}')"


def main(argumentos: List[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        pares = parsear_pares(argumentos)
    except ValueError as e:
        print(f"❌ {e}")
        return 2
    if not pares:
        print("No hay nada que marcar.")
        return 0
    hoy = date.today()
    if hoy.weekday() == 6 or es_festivo(hoy):
        print("Hoy es domingo o festivo: no se marca nada.")
        return 0

    empleados = {e["id"]: e for e in cargar_empleados()}
    fallos = 0
    for emp_id, accion in pares:
        emp = empleados.get(emp_id)
        if not emp:
            print(f"✖ {emp_id}: no existe o está desactivado")
            fallos += 1
        elif esta_ocupado(bitacora.leer_eventos(), emp_id, datetime.now(), os.getpid()):
            print(f"⏭ {emp['nombre']}: otro proceso lo está atendiendo ahora; se omite")
        else:
            try:
                linea = marcar(emp, accion)
            except Exception as e:  # un fallo con un empleado no debe frenar al resto
                linea = f"✖ {emp['nombre']}: error inesperado ({type(e).__name__})"
            print(linea)
            fallos += linea.startswith("✖")
    print(f"\n{len(pares) - fallos} de {len(pares)} sin problema.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
