"""Lógica pura de scripts/probar_login.py: elegir empleado, revisar credenciales y clasificar fallos.

Está separada del script para poder probarla sin navegador. Nada de lo que devuelve incluye
la contraseña.
"""
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv

from src.empleados import EMPLOYEES_FILE


def leer_empleados(ruta: Path = EMPLOYEES_FILE) -> List[Dict]:
    """Todos los empleados configurados, incluidos los desactivados (cargar_empleados() los descarta)."""
    if ruta.exists():
        with open(ruta, "r", encoding="utf-8") as f:
            return list(json.load(f).get("employees", []))

    load_dotenv()
    usuario = os.getenv("GEOVICTORIA_USER")
    password = os.getenv("GEOVICTORIA_PASSWORD")
    if not usuario or not password:
        raise ValueError("No hay config/employees.json ni GEOVICTORIA_USER/GEOVICTORIA_PASSWORD en .env")
    return [{"id": "default", "nombre": usuario, "usuario": usuario, "password": password, "activo": True}]


def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar sin depender de cómo se escribió."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).casefold()


def elegir_empleado(empleados: List[Dict], selector: str) -> Dict:
    """Elige por id exacto o por un fragmento único del nombre."""
    buscado = _normalizar(selector.strip())
    if not buscado:
        raise ValueError("Indica un id o parte del nombre")

    por_id = [e for e in empleados if _normalizar(str(e.get("id", ""))) == buscado]
    if len(por_id) == 1:
        return por_id[0]

    coincidencias = [e for e in empleados if buscado in _normalizar(str(e.get("nombre", "")))]
    if len(coincidencias) == 1:
        return coincidencias[0]
    if not coincidencias:
        raise ValueError(f"Ningún empleado coincide con '{selector}'")
    nombres = ", ".join(f"{e.get('id')} ({e.get('nombre')})" for e in coincidencias)
    raise ValueError(f"'{selector}' es ambiguo: {nombres}")


def revisar_credenciales(usuario: str, password: str) -> List[str]:
    """Avisos sobre problemas típicos de copiar y pegar. Nunca incluye la contraseña."""
    avisos = []
    for nombre, vacio, valor in (("El usuario", "vacío", usuario), ("La contraseña", "vacía", password)):
        if not valor:
            avisos.append(f"{nombre} está {vacio}")
            continue
        if valor != valor.strip():
            avisos.append(f"{nombre} empieza o termina con espacios")
        raros = {f"U+{ord(c):04X}" for c in valor if c != " " and unicodedata.category(c)[0] in ("C", "Z")}
        if raros:
            avisos.append(
                f"{nombre} contiene caracteres invisibles ({', '.join(sorted(raros))}), "
                "típicos de copiar desde Word o un correo"
            )
    if usuario and " " in usuario.strip():
        avisos.append("El usuario contiene espacios en medio")
    return avisos


# (código, patrón sobre URL+texto normalizado, explicación). El orden importa: lo más específico primero.
_PATRONES = [
    (
        "navegador_no_soportado",
        r"browsernotsupported|navegador no (esta )?soportado|browser not supported",
        "El portal detectó un navegador no soportado (posible detección de automatización).",
    ),
    (
        "cuenta_bloqueada",
        r"bloquead|inhabilitad|suspendid|locked|demasiados intentos|too many",
        "El portal indica que la cuenta está bloqueada o hubo demasiados intentos. Seguir probando "
        "empeora el bloqueo: espera o pide que la desbloqueen.",
    ),
    (
        "captcha",
        r"captcha|no soy un robot|not a robot",
        "El portal pide un captcha, que el programador no puede resolver.",
    ),
    (
        "segundo_factor",
        r"codigo de verificacion|verification code|autenticacion en dos|two.factor|2fa|mfa|authenticator",
        "El portal pide un segundo factor o código de verificación: esa cuenta no sirve para un "
        "marcaje automático mientras esté activo.",
    ),
    (
        "cambio_clave",
        r"cambi\w* (de |su |tu |la )?(contrasena|clave)|change (your )?password|(contrasena|clave) (ha )?(expirad|vencid)",
        "El portal pide cambiar la contraseña (primer ingreso o clave vencida). Entra a mano, "
        "cámbiala y actualiza employees.json.",
    ),
    (
        "credenciales_rechazadas",
        r"incorrect|invalid|no (es )?valid|equivocad|no coincid",
        "El portal rechazó el usuario o la contraseña. Revisa employees.json y prueba entrar a mano en el portal.",
    ),
]

_SIN_SENAL = (
    "sin_senal",
    "El portal no mostró ningún mensaje reconocible. Puede ser lentitud o red, o que el login "
    "cambió (revisa config/selectors.json); mira la captura.",
)


def clasificar_resultado(url: str, texto: str) -> Tuple[str, str]:
    """Posible causa de un login fallido a partir de la URL final y el texto visible del portal."""
    base = _normalizar(f"{url}\n{texto}")
    for codigo, patron, explicacion in _PATRONES:
        if re.search(patron, base):
            return codigo, explicacion
    return _SIN_SENAL


def resumir_texto(texto: str, limite: int = 500) -> str:
    """Texto en una sola línea y recortado, para mostrarlo como evidencia."""
    plano = re.sub(r"\s+", " ", texto or "").strip()
    return plano if len(plano) <= limite else plano[:limite].rstrip() + "…"
