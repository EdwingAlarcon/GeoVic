"""Logs diarios sin renombrar: el fallo de producción era WinError 32 al rotar un log abierto."""
import logging
from datetime import date

from src.log_diario import ArchivoDiario, StderrDiario, ruta_del_dia

D1, D2 = date(2026, 11, 19), date(2026, 11, 20)


class Reloj:
    def __init__(self, dia):
        self.dia = dia

    def __call__(self):
        return self.dia


def _logger(handler, nombre):
    lg = logging.getLogger(nombre)
    lg.handlers[:] = [handler]
    lg.propagate = False
    lg.setLevel(logging.INFO)
    return lg


def test_cambia_de_archivo_al_cambiar_de_dia_sin_renombrar(tmp_path):
    reloj = Reloj(D1)
    h = ArchivoDiario(tmp_path, "programador", hoy=reloj)
    lg = _logger(h, "t_dia")
    lg.info("linea del dia 1")
    reloj.dia = D2
    lg.info("linea del dia 2")
    h.close()

    dia1, dia2 = ruta_del_dia(tmp_path, "programador", D1), ruta_del_dia(tmp_path, "programador", D2)
    assert "linea del dia 1" in dia1.read_text(encoding="utf-8")
    assert "linea del dia 2" not in dia1.read_text(encoding="utf-8")
    assert "linea del dia 2" in dia2.read_text(encoding="utf-8")
    assert sorted(p.name for p in tmp_path.iterdir()) == [dia1.name, dia2.name]  # nada renombrado


def test_limpieza_se_ejecuta_al_cambiar_de_dia_y_sus_errores_no_rompen_el_log(tmp_path):
    reloj, llamadas = Reloj(D1), []

    def limpiar():
        llamadas.append(1)
        raise OSError("disco ocupado")

    h = ArchivoDiario(tmp_path, "programador", al_cambiar_dia=limpiar, hoy=reloj)
    lg = _logger(h, "t_limpieza")
    lg.info("a")
    assert llamadas == []
    reloj.dia = D2
    lg.info("b")
    lg.info("c")
    h.close()
    assert llamadas == [1]  # una vez por cambio de día, no por línea
    assert "c" in ruta_del_dia(tmp_path, "programador", D2).read_text(encoding="utf-8")


def test_otro_lector_con_el_archivo_abierto_no_provoca_errores(tmp_path, monkeypatch):
    """El caso de producción: alguien tiene el log abierto mientras se escribe y cambia el día."""
    reloj, errores = Reloj(D1), []
    h = ArchivoDiario(tmp_path, "programador", hoy=reloj)
    monkeypatch.setattr(h, "handleError", lambda record: errores.append(record))
    lg = _logger(h, "t_bloqueo")
    lg.info("antes")
    with open(ruta_del_dia(tmp_path, "programador", D1), "rb"):  # p. ej. el monitor o ver_log_en_vivo
        for i in range(200):
            lg.info("linea %d", i)
        reloj.dia = D2
        lg.info("despues del cambio")
    h.close()
    assert errores == []
    assert "despues del cambio" in ruta_del_dia(tmp_path, "programador", D2).read_text(encoding="utf-8")


def test_stderr_va_a_su_propio_archivo_diario(tmp_path):
    reloj = Reloj(D1)
    err = StderrDiario(tmp_path, "errores_programador", hoy=reloj)
    err.write("Traceback 1\n")
    reloj.dia = D2
    err.write("Traceback 2\n")
    assert ruta_del_dia(tmp_path, "errores_programador", D1).read_text(encoding="utf-8") == "Traceback 1\n"
    assert ruta_del_dia(tmp_path, "errores_programador", D2).read_text(encoding="utf-8") == "Traceback 2\n"
    assert not hasattr(err, "closed")  # Playwright entonces no pide fileno() y hereda la consola
