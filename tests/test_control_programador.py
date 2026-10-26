"""Tests de control_programador: solo debe tocar procesos del programador, nunca otros python."""
import subprocess
import sys
import time
from types import SimpleNamespace

import psutil

from src import control_programador as cp


def _falso(nombre, cmdline):
    return SimpleNamespace(info={"name": nombre, "cmdline": cmdline})


def test_reconoce_solo_procesos_python_de_programador():
    assert cp._es_programador(_falso("python.exe", ["python.exe", "src\\programador.py"]))
    assert cp._es_programador(_falso("python", ["/venv/bin/python", "src/programador.py"]))
    assert not cp._es_programador(_falso("python.exe", ["python.exe", "scripts\\monitor.py"]))
    assert not cp._es_programador(_falso("notepad.exe", ["notepad.exe", "programador.py"]))
    assert not cp._es_programador(_falso("python.exe", None))


def test_la_consola_cmd_solo_cuenta_si_se_piden_las_ventanas():
    ventana = _falso("cmd.exe", ["cmd", "/k", "python.exe", "src\\programador.py"])
    assert not cp._es_programador(ventana)                        # saber si "corre" mira solo el python
    assert cp._es_programador(ventana, incluir_ventanas=True)     # cerrar sí incluye su consola
    assert not cp._es_programador(_falso("cmd.exe", ["cmd", "/c", "otra_cosa.bat"]), incluir_ventanas=True)
    assert not cp._es_programador(_falso("notepad.exe", ["programador.py"]), incluir_ventanas=True)


def _dormir(*marcadores):
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)", *marcadores],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_detener_cierra_el_programador_y_no_otros_procesos(monkeypatch):
    objetivo, inocente = _dormir("programador.py"), _dormir("otra_cosa.py")
    try:
        # Solo se ofrece el objetivo: un programador real de esta máquina no debe entrar en el test.
        monkeypatch.setattr(cp, "procesos_programador", lambda **kw: [psutil.Process(objetivo.pid)])
        assert cp.detener(espera_seg=5) == 1
        assert objetivo.wait(timeout=5) is not None
        time.sleep(0.3)
        assert inocente.poll() is None  # sigue vivo
    finally:
        for p in (objetivo, inocente):
            p.kill()
            p.wait()


def test_detener_sin_programador_no_falla(monkeypatch):
    monkeypatch.setattr(cp, "procesos_programador", lambda **kw: [])
    assert cp.detener() == 0


def test_detener_pide_tambien_las_ventanas_de_consola(monkeypatch):
    pedido = {}
    monkeypatch.setattr(cp, "procesos_programador", lambda **kw: pedido.update(kw) or [])
    cp.detener()
    assert pedido == {"incluir_ventanas": True}  # si no, quedan consolas vacías acumuladas


def test_iniciar_lanza_con_la_ruta_y_el_script_indicados(monkeypatch, tmp_path):
    llamadas = {}

    class FalsoPopen:
        def __init__(self, cmd, **kw):
            llamadas.update(cmd=cmd, kw=kw)
            self.pid = 4242

    monkeypatch.setattr(cp.subprocess, "Popen", FalsoPopen)
    assert cp.iniciar(tmp_path, python="py") == 4242
    assert llamadas["kw"]["cwd"] == str(tmp_path)
    if sys.platform == "win32":
        # Abre una consola visible ("cmd /k"): una sola cadena, con las comillas externas que cmd necesita.
        linea = llamadas["cmd"]
        assert isinstance(linea, str) and linea.startswith("cmd /c start ")
        assert '"Programador GeoVictoria"' in linea and f'/D "{tmp_path}"' in linea
        assert 'cmd /k ""py" ' in linea and linea.endswith('programador.py"')
    else:
        assert llamadas["cmd"][0] == "py" and llamadas["cmd"][1].endswith("programador.py")


def test_lanzar_marcado_pasa_los_pares_al_script(monkeypatch, tmp_path):
    llamadas = {}

    class FalsoPopen:
        def __init__(self, cmd, **kw):
            llamadas.update(cmd=cmd, kw=kw)
            self.pid = 77

    monkeypatch.setattr(cp.subprocess, "Popen", FalsoPopen)
    pendientes = [{"id": "emp4", "nombre": "Ana", "accion": "salida"}, {"id": "emp2", "nombre": "Luis", "accion": "entrada"}]
    assert cp.lanzar_marcado(tmp_path, pendientes, python="py") == 77
    assert llamadas["cmd"][0] == "py" and llamadas["cmd"][1].endswith("marcar_pendientes.py")
    assert llamadas["cmd"][2:] == ["emp4:salida", "emp2:entrada"]  # solo ids y acción, nunca credenciales
    assert llamadas["kw"]["cwd"] == str(tmp_path)
