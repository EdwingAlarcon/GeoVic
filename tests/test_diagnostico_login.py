"""Tests de diagnostico_login: lógica pura de scripts/probar_login.py (sin navegador)."""
import json

import pytest

from src import diagnostico_login as dl

EMPLEADOS = [
    {"id": "emp1", "nombre": "Sergio Giraldo", "usuario": "u1", "password": "p1", "activo": True},
    {"id": "emp15", "nombre": "Gerhart Joan Castillo Cortes", "usuario": "u15", "password": "p15", "activo": False},
    {"id": "emp3", "nombre": "Heiner Lozano", "usuario": "u3", "password": "p3", "activo": True},
    {"id": "emp4", "nombre": "Heiner Martínez", "usuario": "u4", "password": "p4", "activo": True},
]


# --- elegir_empleado ---------------------------------------------------------

def test_elegir_por_id_sin_importar_mayusculas():
    assert dl.elegir_empleado(EMPLEADOS, "EMP15")["nombre"].startswith("Gerhart")


def test_elegir_por_nombre_sin_tildes_ni_mayusculas():
    assert dl.elegir_empleado(EMPLEADOS, "martinez")["id"] == "emp4"
    assert dl.elegir_empleado(EMPLEADOS, " GERHART ")["id"] == "emp15"


def test_elegir_ambiguo_lista_las_opciones():
    with pytest.raises(ValueError, match="ambiguo"):
        dl.elegir_empleado(EMPLEADOS, "heiner")


def test_elegir_inexistente_o_vacio():
    with pytest.raises(ValueError, match="Ningún empleado"):
        dl.elegir_empleado(EMPLEADOS, "zzz")
    with pytest.raises(ValueError):
        dl.elegir_empleado(EMPLEADOS, "   ")


# --- leer_empleados ----------------------------------------------------------

def test_leer_empleados_incluye_desactivados(tmp_path):
    ruta = tmp_path / "employees.json"
    ruta.write_text(json.dumps({"employees": EMPLEADOS}), encoding="utf-8")
    leidos = dl.leer_empleados(ruta)
    assert [e["id"] for e in leidos] == ["emp1", "emp15", "emp3", "emp4"]  # emp15 está inactivo y aparece


def test_leer_empleados_sin_archivo_usa_el_env(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "load_dotenv", lambda *a, **k: None)  # no leer el .env real
    monkeypatch.setenv("GEOVICTORIA_USER", "solo")
    monkeypatch.setenv("GEOVICTORIA_PASSWORD", "clave")
    leidos = dl.leer_empleados(tmp_path / "no_existe.json")
    assert leidos[0]["id"] == "default" and leidos[0]["usuario"] == "solo"


def test_leer_empleados_sin_nada_falla(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("GEOVICTORIA_USER", raising=False)
    monkeypatch.delenv("GEOVICTORIA_PASSWORD", raising=False)
    with pytest.raises(ValueError):
        dl.leer_empleados(tmp_path / "no_existe.json")


# --- revisar_credenciales ----------------------------------------------------

def test_credenciales_limpias_no_dan_avisos():
    assert dl.revisar_credenciales("usuario.ok", "Clave con espacios 123") == []


def test_detecta_espacios_y_caracteres_invisibles():
    assert any("espacios" in a for a in dl.revisar_credenciales("usuario ", "ok"))
    assert any("U+00A0" in a for a in dl.revisar_credenciales("ok", "clave "))
    assert any("U+200B" in a for a in dl.revisar_credenciales("us​uario", "ok"))
    assert any("espacios en medio" in a for a in dl.revisar_credenciales("juan perez", "ok"))


def test_detecta_vacios():
    avisos = dl.revisar_credenciales("", "")
    assert avisos == ["El usuario está vacío", "La contraseña está vacía"]


def test_los_avisos_nunca_incluyen_la_contrasena():
    secreto = "S3cr3t0-Unico"
    avisos = dl.revisar_credenciales("u", secreto + " ")
    assert avisos and not any(secreto in a for a in avisos)


# --- clasificar_resultado ----------------------------------------------------

@pytest.mark.parametrize(
    "url, texto, esperado",
    [
        ("https://x/browsernotsupported", "", "navegador_no_soportado"),
        ("https://x/login", "Su cuenta ha sido bloqueada", "cuenta_bloqueada"),
        ("https://x/login", "Demasiados intentos, espere", "cuenta_bloqueada"),
        ("https://x/login", "Protegido por reCAPTCHA", "captcha"),
        ("https://x/login", "Ingrese el código de verificación", "segundo_factor"),
        ("https://x/changepassword", "Debe cambiar su contraseña", "cambio_clave"),
        ("https://x/login", "Usuario o contraseña incorrectos", "credenciales_rechazadas"),
        ("https://x/login", "Invalid username or password", "credenciales_rechazadas"),
    ],
)
def test_clasifica_las_causas_conocidas(url, texto, esperado):
    assert dl.clasificar_resultado(url, texto)[0] == esperado


def test_la_pagina_de_login_normal_no_es_un_error():
    # Las etiquetas del propio formulario no deben confundirse con un mensaje de error
    assert dl.clasificar_resultado("https://x/login", "Usuario Contraseña Ingresar Olvidé mi contraseña")[0] == "sin_senal"


def test_toda_clasificacion_trae_explicacion():
    codigo, explicacion = dl.clasificar_resultado("https://x/login", "")
    assert codigo == "sin_senal" and explicacion


# --- resumir_texto -----------------------------------------------------------

def test_resumir_texto_compacta_y_recorta():
    assert dl.resumir_texto("a \n\n  b\tc") == "a b c"
    largo = dl.resumir_texto("x" * 1000, limite=10)
    assert largo == "x" * 10 + "…"
    assert dl.resumir_texto(None) == ""
