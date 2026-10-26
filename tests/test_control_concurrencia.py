"""Tests de control_concurrencia: instancia única y cupo de navegadores."""
import asyncio
import subprocess
import sys
import threading
import uuid
from pathlib import Path

import pytest

from src import control_concurrencia as cc

RAIZ = Path(__file__).parent.parent


def _nombre_unico() -> str:
    # Un nombre por test: no choca con un programador real ni con otros tests
    return f"Global\\GeoVictoriaTest_{uuid.uuid4().hex}"


# --- Instancia única ---------------------------------------------------------

def test_segunda_adquisicion_es_rechazada(tmp_path):
    nombre, guard = _nombre_unico(), tmp_path / "t.guard"
    cc.adquirir_instancia_unica(guard, nombre)
    with pytest.raises(cc.InstanciaYaEnEjecucion):
        cc.adquirir_instancia_unica(guard, nombre)


_HIJO = """
import sys
sys.path.insert(0, {raiz!r})
from pathlib import Path
from src import control_concurrencia as cc
cc.adquirir_instancia_unica(Path({guard!r}), {nombre!r})
print("listo", flush=True)
sys.stdin.readline()  # vive hasta que el test cierre su stdin
"""


def test_otro_proceso_es_rechazado_y_se_libera_al_morir(tmp_path):
    nombre, guard = _nombre_unico(), tmp_path / "t.guard"
    hijo = subprocess.Popen(
        [sys.executable, "-c", _HIJO.format(raiz=str(RAIZ), guard=str(guard), nombre=nombre)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    try:
        assert hijo.stdout.readline().strip() == "listo"

        # El hijo vivo tiene la exclusión: no se puede tomar desde aquí
        with pytest.raises(cc.InstanciaYaEnEjecucion):
            cc.adquirir_instancia_unica(guard, nombre)
    finally:
        hijo.stdin.close()
        hijo.wait(timeout=15)

    # Muerto el hijo el sistema operativo libera la exclusión sola (reinicio, kill, crash)
    cc.adquirir_instancia_unica(guard, nombre)


# --- Cupo de navegadores -----------------------------------------------------

def _correr_en_hilo(corrutina_fn, timeout=10):
    """Ejecuta la corrutina en su propio hilo/loop (como hace el scheduler) y espera."""
    resultado = {}

    def objetivo():
        try:
            resultado["valor"] = asyncio.run(corrutina_fn())
        except BaseException as e:  # noqa: BLE001 - se propaga al test
            resultado["error"] = e

    hilo = threading.Thread(target=objetivo)
    hilo.start()
    hilo.join(timeout)
    assert not hilo.is_alive(), "el trabajo quedó colgado (¿cupo sin liberar?)"
    if "error" in resultado:
        raise resultado["error"]
    return resultado.get("valor")


def test_cupo_limita_navegadores_simultaneos():
    cupo = cc.CupoNavegador(2)
    candado = threading.Lock()
    estado = {"activos": 0, "maximo": 0}

    async def trabajo():
        async with cupo.reservar("[t] "):
            with candado:
                estado["activos"] += 1
                estado["maximo"] = max(estado["maximo"], estado["activos"])
            await asyncio.sleep(0.2)
            with candado:
                estado["activos"] -= 1

    hilos = [threading.Thread(target=lambda: asyncio.run(trabajo())) for _ in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(30)

    assert not any(h.is_alive() for h in hilos)
    assert estado["maximo"] == 2


def test_cupo_se_libera_si_el_trabajo_falla():
    cupo = cc.CupoNavegador(1)

    async def falla():
        async with cupo.reservar():
            raise RuntimeError("boom")

    async def exito():
        async with cupo.reservar():
            return True

    with pytest.raises(RuntimeError):
        _correr_en_hilo(falla)
    assert _correr_en_hilo(exito) is True  # se colgaría si el cupo no se hubiera liberado


def test_maximo_desde_entorno(monkeypatch):
    monkeypatch.delenv("GEOVICTORIA_MAX_NAVEGADORES", raising=False)
    assert cc.maximo_navegadores_desde_entorno() == 3

    monkeypatch.setenv("GEOVICTORIA_MAX_NAVEGADORES", "5")
    assert cc.maximo_navegadores_desde_entorno() == 5

    monkeypatch.setenv("GEOVICTORIA_MAX_NAVEGADORES", "0")
    assert cc.maximo_navegadores_desde_entorno() == 1  # nunca menos de 1

    monkeypatch.setenv("GEOVICTORIA_MAX_NAVEGADORES", "abc")
    assert cc.maximo_navegadores_desde_entorno() == 3  # inválido: usa el defecto


def test_desactivar_seleccion_consola_nunca_rompe_sin_consola():
    # En pytest la entrada estándar no es una consola: debe devolver False sin lanzar.
    assert cc.desactivar_seleccion_consola() in (False, True)


def test_desactivar_seleccion_consola_no_hace_nada_fuera_de_windows(monkeypatch):
    monkeypatch.setattr(cc.sys, "platform", "linux")
    assert cc.desactivar_seleccion_consola() is False
