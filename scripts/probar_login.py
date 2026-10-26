#!/usr/bin/env python3
"""
Prueba el login de UN empleado en GeoVictoria, SIN marcar, y explica por qué falla.

Uso:
  python scripts/probar_login.py                  # lista los empleados y pregunta cuál
  python scripts/probar_login.py emp15            # por id
  python scripts/probar_login.py gerhart          # o por parte del nombre
  python scripts/probar_login.py emp15 --si       # sin pedir confirmación
  python scripts/probar_login.py emp15 --headless # sin ventana (el portal puede detectarlo)

Prueba también a empleados desactivados ("activo": false). No hace clic en ningún botón de
marcaje. Cada prueba cuenta como un intento de login: si la cuenta tiene un problema, varios
intentos seguidos pueden bloquearla.
"""
import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from src import diagnostico_login as dl
from src.geovictoria import (
    _SEL,
    Config,
    _crear_contexto_browser,
    verificar_boton_disponible,
    wait_for_iframe,
)

# El informe se imprime con print() y ya incluye lo que loguea geovictoria (iframe no encontrado, etc.)
logging.getLogger("src.geovictoria").setLevel(logging.CRITICAL)

LOGS = Path(__file__).parent.parent / "src" / "logs"
SELECTOR_ERRORES = (
    "[role=alert], .validation-summary-errors, .field-validation-error, .alert, "
    ".text-danger, [class*='error'], [class*='invalid']"
)


def _listar(empleados):
    print("\nEmpleados configurados:")
    for i, e in enumerate(empleados, 1):
        estado = "" if e.get("activo", True) else "  (desactivado)"
        print(f"  {i:2d}. {str(e.get('id')):8s} {e.get('nombre')}{estado}")


def _pedir_empleado(empleados):
    _listar(empleados)
    while True:
        eleccion = input("\nNúmero, id o parte del nombre: ").strip()
        if eleccion.isdigit() and 1 <= int(eleccion) <= len(empleados):
            return empleados[int(eleccion) - 1]
        try:
            return dl.elegir_empleado(empleados, eleccion)
        except ValueError as e:
            print(f"  ⚠️  {e}")


async def _texto_visible(page) -> str:
    try:
        return await page.inner_text("body", timeout=3000)
    except Exception:
        return ""


async def _mensajes_de_error(page) -> list:
    try:
        textos = await page.locator(SELECTOR_ERRORES).all_inner_texts()
    except Exception:
        return []
    vistos = []
    for t in (x.strip() for x in textos):
        if t and t not in vistos:
            vistos.append(t)
    return vistos


async def _capturar(page, emp) -> str:
    LOGS.mkdir(exist_ok=True)
    ruta = LOGS / f"probar_login_{emp.get('id')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    try:
        await page.screenshot(path=str(ruta), full_page=True)
        return str(ruta)
    except Exception:
        return ""


async def probar(emp, headless: bool, url: str) -> dict:
    """Hace el login SIN marcar nada y devuelve la evidencia."""
    r = {"salio_del_login": False, "url": "", "texto": "", "mensajes": [], "captura": "",
         "iframe": None, "boton": None, "error": ""}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        try:
            context = await browser.new_context(**_crear_contexto_browser())
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded")
                await page.fill(_SEL["login"]["username"], emp["usuario"])
                await page.fill(_SEL["login"]["password"], emp["password"])
                await page.click(_SEL["login"]["submit"])
                try:
                    await page.wait_for_url(lambda u: "login" not in u, timeout=Config.LOGIN_TIMEOUT)
                    r["salio_del_login"] = True
                except PlaywrightTimeoutError:
                    pass
            except Exception as e:  # selector del login no encontrado, red caída, etc.
                r["error"] = str(e).splitlines()[0][:200]

            r["url"] = page.url
            r["texto"] = await _texto_visible(page)
            r["mensajes"] = await _mensajes_de_error(page)

            if r["salio_del_login"] and "browsernotsupported" not in page.url:
                frame = await wait_for_iframe(page, max_retries=2)
                r["iframe"] = frame is not None
                if frame:
                    r["boton"] = await verificar_boton_disponible(frame)

            if not (r["salio_del_login"] and r["iframe"]):
                r["captura"] = await _capturar(page, emp)
        finally:
            await browser.close()
    return r


def _veredicto(r):
    """(exito, código de causa, explicación) a partir de la evidencia de `probar`."""
    codigo, explicacion = dl.clasificar_resultado(r["url"], r["texto"] + " " + " ".join(r["mensajes"]))
    exito = bool(r["salio_del_login"] and r["iframe"] and codigo == "sin_senal")
    return exito, codigo, explicacion


def _linea_resumen(emp, r) -> str:
    exito, codigo, explicacion = _veredicto(r)
    if exito and r["boton"] == "Salida":
        estado = "✅ login OK · el portal ofrece 'Marcar Salida' → la ENTRADA ya está registrada"
    elif exito and r["boton"] == "Entrada":
        estado = "⚠️  login OK · el portal ofrece 'Marcar Entrada' → la ENTRADA NO está registrada"
    elif exito:
        estado = "✅ login OK · sin botón de marcaje visible (jornada completa o fuera de horario)"
    elif r["salio_del_login"] and r["iframe"] is False and codigo == "sin_senal":
        estado = "⚠️  login OK · no se encontró el módulo de marcaje (iframe)"
    elif r["error"] and codigo == "sin_senal":
        estado = f"❌ no se pudo hacer el login: {r['error'][:80]}"
    else:
        estado = f"❌ login fallido · {explicacion[:90]}"
    extra = f"  [captura: {Path(r['captura']).name}]" if r["captura"] else ""
    return f"{str(emp.get('id')):6s} {str(emp.get('nombre'))[:34]:35s} {estado}{extra}"


async def probar_todos(empleados, headless: bool, url: str) -> int:
    """Login de cada empleado en secuencia (uno por uno, nunca en paralelo) y una línea por cada uno."""
    fallos = 0
    for emp in empleados:
        avisos = dl.revisar_credenciales(emp.get("usuario", ""), emp.get("password", ""))
        r = await probar(emp, headless, url)
        print(_linea_resumen(emp, r) + ("   ⚠️ " + "; ".join(avisos) if avisos else ""), flush=True)
        fallos += 0 if _veredicto(r)[0] else 1
    return fallos


def _informe(emp, avisos, r) -> int:
    """Imprime el diagnóstico y devuelve el código de salida (0 = login correcto)."""
    print("\n" + "=" * 70)
    print(f"  {emp.get('id')} - {emp.get('nombre')}"
          + ("" if emp.get("activo", True) else "  (desactivado)"))
    print("=" * 70)

    print("\nCredenciales en employees.json:")
    if avisos:
        for a in avisos:
            print(f"  ⚠️  {a}")
    else:
        print("  ✅ Sin problemas evidentes (espacios, caracteres invisibles)")

    print("\nResultado del login:")
    exito, codigo, explicacion = _veredicto(r)

    if exito and r["boton"]:
        print(f"  ✅ Login correcto. El portal ofrece 'Marcar {r['boton']}'.")
    elif exito:
        print("  ✅ Login correcto, pero ningún botón de marcaje visible (fuera de horario o jornada ya completa).")
    elif r["salio_del_login"] and r["iframe"] is False and codigo == "sin_senal":
        print("  ⚠️  El login pasó, pero no se encontró el módulo de marcaje (iframe).")
        print("     Posibles causas: el portal cambió, o esta cuenta no tiene el marcaje habilitado.")
    elif r["error"] and codigo == "sin_senal":
        print(f"  ❌ No se pudo completar el login: {r['error']}")
        print("     Posible causa: el formulario cambió (revisa config/selectors.json) o no hay conexión.")
    else:
        print(f"  ❌ Login fallido. Posible causa: {explicacion}")

    print("\nEvidencia:")
    print(f"  • URL final: {r['url']}")
    if r["mensajes"]:
        print(f"  • Mensaje del portal: {dl.resumir_texto(' | '.join(r['mensajes']), 300)}")
    elif not exito:
        print(f"  • Texto visible: {dl.resumir_texto(r['texto'], 300) or '(vacío)'}")
    if r["captura"]:
        print(f"  • Captura: {r['captura']}")

    print()
    return 0 if exito else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba el login de un empleado, sin marcar.")
    parser.add_argument("empleado", nargs="?", help="id o parte del nombre (si se omite, se pregunta)")
    parser.add_argument("--headless", action="store_true", help="sin ventana (el portal puede detectarlo)")
    parser.add_argument("--si", action="store_true", help="no pedir confirmación")
    parser.add_argument("--todos", action="store_true", help="probar a todos los empleados activos, uno tras otro")
    parser.add_argument("--incluir-desactivados", action="store_true", help="con --todos, incluir a los desactivados")
    parser.add_argument("--url", default=Config.LOGIN_URL, help="URL del login (para pruebas)")
    parser.add_argument("--empleados", default=str(dl.EMPLOYEES_FILE), help="ruta de employees.json (para pruebas)")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.todos:
        try:
            empleados = [e for e in dl.leer_empleados(Path(args.empleados))
                         if args.incluir_desactivados or e.get("activo", True)]
        except ValueError as e:
            print(f"❌ {e}")
            return 2
        if not args.si:
            print(f"\nSe probará el login de {len(empleados)} empleados, uno tras otro, en el portal REAL.")
            print("Cada prueba cuenta como un intento de login; no se marca nada.")
            try:
                input("Enter para continuar (Ctrl+C para cancelar)... ")
            except (EOFError, KeyboardInterrupt):
                print("\nCancelado.")
                return 2
        print(f"\nProbando {len(empleados)} empleados (una ventana a la vez; unos 15-20 s cada uno)...\n", flush=True)
        fallos = asyncio.run(probar_todos(empleados, args.headless, args.url))
        print(f"\nResumen: {len(empleados) - fallos} correctos · {fallos} con problema(s)\n")
        return 0 if fallos == 0 else 1

    try:
        empleados = dl.leer_empleados(Path(args.empleados))
        emp = dl.elegir_empleado(empleados, args.empleado) if args.empleado else _pedir_empleado(empleados)
    except ValueError as e:
        print(f"❌ {e}")
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\nCancelado.")
        return 2

    avisos = dl.revisar_credenciales(emp.get("usuario", ""), emp.get("password", ""))

    if not args.si:
        print(f"\nSe probará el login de {emp.get('nombre')} ({emp.get('id')}) en el portal REAL.")
        print("Cada prueba cuenta como un intento de login; no se marca nada.")
        try:
            input("Enter para continuar (Ctrl+C para cancelar)... ")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelado.")
            return 2

    print("\nProbando el login (puede tardar hasta ~1 minuto)...")
    resultado = asyncio.run(probar(emp, args.headless, args.url))
    return _informe(emp, avisos, resultado)


if __name__ == "__main__":
    sys.exit(main())
