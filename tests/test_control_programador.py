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


def _dormir(*marcadores):
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)", *marcadores],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_detener_cierra_el_programador_y_no_otros_procesos(monkeypatch):
    objetivo, inocente = _dormir("programador.py"), _dormir("otra_cosa.py")
    try:
        # Solo se ofrece el objetivo: un programador real de esta máquina no debe entrar en el test.
        monkeypatch.setattr(cp, "procesos_programador", lambda: [psutil.Process(objetivo.pid)])
        assert cp.detener(espera_seg=5) == 1
        assert objetivo.wait(timeout=5) is not None
        time.sleep(0.3)
        assert inocente.poll() is None  # sigue vivo
    finally:
        for p in (objetivo, inocente):
            p.kill()
            p.wait()


def test_detener_sin_programador_no_falla(monkeypatch):
    monkeypatch.setattr(cp, "procesos_programador", lambda: [])
    assert cp.detener() == 0


def test_iniciar_lanza_con_la_ruta_y_el_script_indicados(monkeypatch, tmp_path):
    llamadas = {}

    class FalsoPopen:
        def __init__(self, cmd, **kw):
            llamadas.update(cmd=cmd, kw=kw)
            self.pid = 4242

    monkeypatch.setattr(cp.subprocess, "Popen", FalsoPopen)
    assert cp.iniciar(tmp_path, python="py") == 4242
    assert llamadas["cmd"][0] == "py" and llamadas["cmd"][1].endswith("programador.py")
    assert llamadas["kw"]["cwd"] == str(tmp_path)
    if sys.platform == "win32":
        assert llamadas["kw"]["creationflags"] & cp.subprocess.CREATE_NO_WINDOW
