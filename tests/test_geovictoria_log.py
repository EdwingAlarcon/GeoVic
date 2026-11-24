"""El log de geovictoria.py no debe guardar el usuario completo del portal (sirve para atacar el login)."""
import pytest

from src.geovictoria import enmascarar_usuario


@pytest.mark.parametrize("usuario, esperado", [
    ("ana.perez@empresa.com", "an***@empresa.com"),
    ("1234567890", "12***"),
    ("ab", "***"),
    ("x@y.co", "***@y.co"),
    ("", "***"),
    (None, "***"),
])
def test_enmascara_el_usuario(usuario, esperado):
    assert enmascarar_usuario(usuario) == esperado


def test_nunca_contiene_el_usuario_completo():
    for usuario in ("ana.perez@empresa.com", "1234567890", "x@y.co"):
        assert usuario not in enmascarar_usuario(usuario)
