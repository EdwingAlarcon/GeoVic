#!/usr/bin/env python3
"""
Cifra con DPAPI las contraseñas en claro de config/employees.json. EJECUTAR EN EL SERVIDOR:
lo cifrado solo se descifra en el equipo donde se cifró.

Uso:
  python scripts/cifrar_credenciales.py            # cifra las que estén en claro (idempotente)
  python scripts/cifrar_credenciales.py --revisar  # solo informa, no escribe

No hace falta detener el programador: lee employees.json al arrancar y descifra en cada login.
Antes de escribir comprueba que cada contraseña cifrada se descifra igual; el archivo se reemplaza de
una vez (nunca queda a medio escribir). No se guarda copia en claro.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import credenciales  # noqa: E402
from src.empleados import EMPLOYEES_FILE  # noqa: E402


def cifrar_archivo(ruta: Path, solo_revisar: bool = False) -> Tuple[int, int]:
    """Cifra las contraseñas en claro. Devuelve (cifradas_ahora, ya_cifradas). Lanza ValueError si algo no cuadra."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    empleados = datos.get("employees") if isinstance(datos, dict) else None
    if not isinstance(empleados, list):
        raise ValueError(f"{ruta} no tiene la lista 'employees'")

    cifradas = ya = 0
    for emp in empleados:
        if not isinstance(emp, dict) or not emp.get("password"):
            continue
        actual = emp["password"]
        if credenciales.esta_cifrada(actual):
            credenciales.revelar(actual)  # si no se descifra aquí, mejor saberlo ya (CredencialIlegible)
            ya += 1
            continue
        if not solo_revisar:
            nueva = credenciales.proteger(actual)
            if credenciales.revelar(nueva) != actual:
                raise ValueError(f"[{emp.get('id')}] la comprobación de ida y vuelta falló; no se escribe nada")
            emp["password"] = nueva
        cifradas += 1

    if cifradas and not solo_revisar:
        fd, temporal = tempfile.mkstemp(prefix=".employees_", suffix=".tmp", dir=str(ruta.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(temporal, ruta)
        except BaseException:
            Path(temporal).unlink(missing_ok=True)
            raise
    return cifradas, ya


def main() -> int:
    parser = argparse.ArgumentParser(description="Cifra con DPAPI las contraseñas de employees.json.")
    parser.add_argument("--revisar", action="store_true", help="solo informa, no escribe")
    parser.add_argument("--empleados", default=str(EMPLOYEES_FILE), help="ruta de employees.json")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ruta = Path(args.empleados)
    if not ruta.exists():
        print(f"❌ No existe {ruta}")
        return 2
    try:
        cifradas, ya = cifrar_archivo(ruta, args.revisar)
    except (ValueError, OSError) as e:
        print(f"❌ {e}\n   No se modificó nada.")
        return 1

    if args.revisar:
        print(f"En claro: {cifradas} · ya cifradas (y legibles aquí): {ya}")
        return 0
    print(f"✅ Cifradas ahora: {cifradas} · ya estaban cifradas: {ya}")
    if cifradas:
        print("\nSiguiente paso: probar_login.bat <id> con UN empleado (no marca nada).")
        print("Si sale bien, BORRA las copias en claro que queden, por ejemplo:")
        print("   respaldo_*\\config\\employees_*.json   y cualquier employees.json copiado a otra carpeta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
