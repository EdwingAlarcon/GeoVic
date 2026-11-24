"""Contraseñas del portal cifradas con DPAPI de Windows dentro de config/employees.json.

Formato: "password": "dpapi:<base64>". Cualquier otro valor se toma como contraseña en claro, que sigue
funcionando (desplegar este código no exige migrar antes, y los reemplazos se dan de alta a mano), pero el
programador avisa al arrancar. Para cifrar: scripts/cifrar_credenciales.bat, EN EL SERVIDOR.

Ámbito LOCAL_MACHINE (no el del usuario): el riesgo que se cubre es que employees.json se lea por la red
(recurso C$) o salga en una copia o respaldo; fuera de este equipo el blob no sirve. Con el ámbito de usuario,
si un administrador RESTABLECE la contraseña de Windows de la cuenta (cuenta local), los blobs quedan
ilegibles y nadie marca. Contrapartida asumida: cualquier proceso de este mismo equipo puede descifrarlas.

Se descifra justo donde se usa (login), nunca al cargar la lista: así la contraseña en claro no vive en los
dicts de empleados que circulan por el programador y el monitor.
"""
import base64
import ctypes
import sys
from typing import Optional

PREFIJO = "dpapi:"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1
_CRYPTPROTECT_LOCAL_MACHINE = 0x4


class CredencialIlegible(ValueError):
    """La contraseña cifrada no se puede descifrar aquí (otro equipo, blob dañado o sistema no Windows)."""


def esta_cifrada(valor: Optional[str]) -> bool:
    return isinstance(valor, str) and valor.startswith(PREFIJO)


if sys.platform == "win32":
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    _crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    _kernel32.LocalFree.restype = ctypes.c_void_p
    for _f in (_crypt32.CryptProtectData, _crypt32.CryptUnprotectData):
        _f.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                       ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
        _f.restype = wintypes.BOOL

    def _dpapi(funcion, datos: bytes, flags: int) -> bytes:
        buffer = ctypes.create_string_buffer(datos, len(datos))
        entrada = _Blob(len(datos), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
        salida = _Blob()
        if not funcion(ctypes.byref(entrada), None, None, None, None, flags, ctypes.byref(salida)):
            raise OSError(ctypes.get_last_error(), "DPAPI rechazó la operación")
        try:
            return ctypes.string_at(salida.pbData, salida.cbData)
        finally:
            _kernel32.LocalFree(salida.pbData)

    def _cifrar(datos: bytes) -> bytes:
        return _dpapi(_crypt32.CryptProtectData, datos, _CRYPTPROTECT_UI_FORBIDDEN | _CRYPTPROTECT_LOCAL_MACHINE)

    def _descifrar(datos: bytes) -> bytes:
        return _dpapi(_crypt32.CryptUnprotectData, datos, _CRYPTPROTECT_UI_FORBIDDEN)
else:
    def _cifrar(datos: bytes) -> bytes:
        raise OSError("DPAPI solo existe en Windows")

    def _descifrar(datos: bytes) -> bytes:
        raise OSError("DPAPI solo existe en Windows")


def proteger(password: str) -> str:
    """Devuelve "dpapi:<base64>". Si ya está cifrada la devuelve tal cual (idempotente)."""
    if esta_cifrada(password):
        return password
    if not password:
        raise ValueError("Contraseña vacía: no hay nada que cifrar")
    return PREFIJO + base64.b64encode(_cifrar(password.encode("utf-8"))).decode("ascii")


def revelar(valor: Optional[str]) -> str:
    """Contraseña en claro para el login. Un valor sin prefijo se devuelve igual (contraseña en claro)."""
    if not esta_cifrada(valor):
        return valor or ""
    try:
        return _descifrar(base64.b64decode(valor[len(PREFIJO):], validate=True)).decode("utf-8")
    except (OSError, ValueError, UnicodeDecodeError) as e:
        raise CredencialIlegible(
            "no se pudo descifrar la contraseña: solo se descifra en el equipo donde se cifró "
            f"(vuelve a ponerla en claro y ejecuta scripts\\cifrar_credenciales.bat ahí) [{type(e).__name__}]"
        ) from None
