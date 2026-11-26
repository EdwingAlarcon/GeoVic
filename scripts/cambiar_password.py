#!/usr/bin/env python3
"""
Cambia la contraseña de GeoVictoria de UN empleado: la pide sin mostrarla, prueba el login con ella
(sin marcar nada) y la guarda YA CIFRADA (DPAPI) en config/employees.json. EJECUTAR EN EL SERVIDOR:
lo cifrado solo se descifra en el equipo donde se cifró.

Uso:
  python scripts/cambiar_password.py                # lista los empleados y pregunta cuál
  python scripts/cambiar_password.py emp6           # por id
  python scripts/cambiar_password.py michael        # o por parte del nombre
  python scripts/cambiar_password.py emp6 --sin-probar   # guarda sin probar el login

La contraseña nunca se escribe en claro en el disco: solo se cambia el campo "password" de ese
empleado y el archivo se reemplaza de una vez. El programador lee employees.json al arrancar, así
que después hay que reiniciarlo (scripts\\reiniciar_programador.bat), lejos de una hora de marcaje.
"""
import argparse
import asyncio
import getpass
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from src import credenciales, diagnostico_login as dl  # noqa: E402

INTENTOS_CLAVE = 3


def guardar_password(ruta: Path, emp_id: str, nueva: str) -> None:
    """Cifra `nueva` y la pone como contraseña del empleado `emp_id`; el resto del archivo queda igual.

    Lanza ValueError si el empleado no existe o está repetido, si la contraseña no vale o si la
    comprobación de ida y vuelta falla; en esos casos no se escribe nada.
    """
    from cifrar_credenciales import escribir_atomico

    if not nueva:
        raise ValueError("la contraseña está vacía")
    if credenciales.esta_cifrada(nueva):
        raise ValueError(f"la contraseña no puede empezar por '{credenciales.PREFIJO}'")

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    empleados = datos.get("employees") if isinstance(datos, dict) else None
    if not isinstance(empleados, list):
        raise ValueError(f"{ruta} no tiene la lista 'employees'")
    coincidencias = [e for e in empleados if isinstance(e, dict) and str(e.get("id")) == str(emp_id)]
    if len(coincidencias) != 1:
        raise ValueError(f"hay {len(coincidencias)} empleados con id '{emp_id}' en {ruta.name} (debe haber 1)")

    cifrada = credenciales.proteger(nueva)
    if credenciales.revelar(cifrada) != nueva:
        raise ValueError("la comprobación de ida y vuelta del cifrado falló")
    coincidencias[0]["password"] = cifrada
    escribir_atomico(ruta, datos)


def pedir_clave_nueva(leer=None) -> str:
    """Pide la contraseña dos veces sin mostrarla. Devuelve "" si se cancela o no coinciden 3 veces."""
    leer = leer or getpass.getpass
    for _ in range(INTENTOS_CLAVE):
        primera = leer("Contraseña NUEVA (no se ve al escribir): ")
        if not primera:
            return ""
        if leer("Repítela: ") == primera:
            return primera
        print("  ⚠️  No coinciden. Otra vez.")
    return ""


def _si(pregunta: str) -> bool:
    try:
        return input(pregunta).strip().lower() in ("s", "si", "sí")
    except (EOFError, KeyboardInterrupt):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Cambia (cifrada) la contraseña de un empleado.")
    parser.add_argument("empleado", nargs="?", help="id o parte del nombre (si se omite, se pregunta)")
    parser.add_argument("--sin-probar", action="store_true", help="guardar sin probar el login")
    parser.add_argument("--headless", action="store_true", help="probar sin ventana (el portal puede detectarlo)")
    parser.add_argument("--url", default=None, help="URL del login (para pruebas)")
    parser.add_argument("--empleados", default=str(dl.EMPLOYEES_FILE), help="ruta de employees.json")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ruta = Path(args.empleados)
    if not ruta.exists():
        print(f"❌ No existe {ruta}")
        return 2
    try:
        empleados = dl.leer_empleados(ruta)
        if args.empleado:
            emp = dl.elegir_empleado(empleados, args.empleado)
        else:
            import probar_login
            emp = probar_login._pedir_empleado(empleados)
    except ValueError as e:
        print(f"❌ {e}")
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\nCancelado.")
        return 2

    print(f"\nCambiar la contraseña de {emp.get('nombre')} ({emp.get('id')})")
    try:
        nueva = pedir_clave_nueva()
    except (EOFError, KeyboardInterrupt):
        nueva = ""
    if not nueva:
        print("\nCancelado. No se modificó nada.")
        return 2

    avisos = dl.revisar_credenciales(emp.get("usuario", ""), nueva)
    for a in avisos:
        print(f"  ⚠️  {a}")
    if avisos and not _si("¿Seguro que la contraseña es así? (s/N): "):
        print("\nCancelado. No se modificó nada.")
        return 2

    if not args.sin_probar:
        import probar_login
        from src.geovictoria import Config
        print("\nProbando el login con la contraseña nueva en el portal REAL (no se marca nada)...")
        r = asyncio.run(probar_login.probar({**emp, "password": nueva}, args.headless, args.url or Config.LOGIN_URL))
        if probar_login._informe(emp, avisos, r) != 0:
            print("El login con la contraseña nueva NO funcionó. Cada intento fallido cuenta en el portal.")
            if not _si("¿Guardarla de todas formas? (s/N): "):
                print("\nNo se modificó nada.")
                return 1

    try:
        guardar_password(ruta, str(emp.get("id")), nueva)
    except (ValueError, OSError) as e:
        print(f"\n❌ {e}\n   No se modificó nada.")
        return 1

    print(f"\n✅ Contraseña de {emp.get('nombre')} guardada CIFRADA en {ruta.name}.")
    print("   Para que el programador la use, reinícialo lejos de una hora de marcaje:")
    print("   scripts\\reiniciar_programador.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
