"""Tests de bitacora: eventos JSONL y latido."""
import json
import threading

from src import bitacora


def _aislar(tmp_path, monkeypatch):
    monkeypatch.setattr(bitacora, "LOG_DIR", tmp_path)


def test_registrar_y_leer(tmp_path, monkeypatch):
    _aislar(tmp_path, monkeypatch)
    bitacora.registrar("login", {"id": "emp1", "nombre": "Ana"}, ok=True, ms=1200)
    bitacora.registrar("programador_inicio", empleados=3)

    eventos = bitacora.leer_eventos()
    assert [e["tipo"] for e in eventos] == ["login", "programador_inicio"]
    assert eventos[0]["emp_id"] == "emp1" and eventos[0]["nombre"] == "Ana" and eventos[0]["ok"] is True
    assert "emp_id" not in eventos[1]
    assert len(eventos[0]["ts"]) == 19  # AAAA-MM-DDTHH:MM:SS


def test_nunca_guarda_usuario_ni_contrasena(tmp_path, monkeypatch):
    _aislar(tmp_path, monkeypatch)
    empleado = {"id": "emp1", "nombre": "Ana", "usuario": "ana@correo.test", "password": "S3cr3t0-Unico"}
    bitacora.registrar("login", empleado, ok=False, motivo="timeout")

    contenido = next(tmp_path.glob("eventos_*.jsonl")).read_text(encoding="utf-8")
    assert "S3cr3t0-Unico" not in contenido and "ana@correo.test" not in contenido


def test_leer_ignora_lineas_truncadas(tmp_path, monkeypatch):
    _aislar(tmp_path, monkeypatch)
    bitacora.registrar("login", ok=True)
    ruta = next(tmp_path.glob("eventos_*.jsonl"))
    with open(ruta, "a", encoding="utf-8") as f:
        f.write('{"ts": "2026-10-26T08:00:00", "tipo": "cor')  # corte a media línea
    assert [e["tipo"] for e in bitacora.leer_eventos()] == ["login"]


def test_leer_sin_archivo_devuelve_vacio(tmp_path, monkeypatch):
    _aislar(tmp_path, monkeypatch)
    assert bitacora.leer_eventos() == []
    assert bitacora.leer_latido() is None


def test_registrar_nunca_rompe_aunque_no_pueda_escribir(tmp_path, monkeypatch):
    archivo = tmp_path / "no_es_carpeta"
    archivo.write_text("x")
    monkeypatch.setattr(bitacora, "LOG_DIR", archivo)  # mkdir/open fallarán
    bitacora.registrar("login", ok=True)  # no debe lanzar
    bitacora.escribir_latido("2026-10-26T08:00:00", "activo", {})  # tampoco


def test_escrituras_concurrentes_no_se_mezclan(tmp_path, monkeypatch):
    _aislar(tmp_path, monkeypatch)

    def escribir(n):
        for i in range(25):
            bitacora.registrar("login", {"id": f"emp{n}", "nombre": f"N{n}"}, ok=True, i=i)

    hilos = [threading.Thread(target=escribir, args=(n,)) for n in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    lineas = next(tmp_path.glob("eventos_*.jsonl")).read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 200
    assert all(json.loads(l)["tipo"] == "login" for l in lineas)  # ninguna línea corrupta


def test_latido_ida_y_vuelta_y_atomico(tmp_path, monkeypatch):
    _aislar(tmp_path, monkeypatch)
    plan = {"emp1": {"mon": {"entrada": "08:00:10", "salida": "17:00:10"}}}
    bitacora.escribir_latido("2026-10-26T08:00:00", "arrancando", plan)
    bitacora.escribir_latido("2026-10-26T08:00:00", "activo", plan, tick_scheduler="2026-10-26T08:01:00")

    latido = bitacora.leer_latido()
    assert latido["fase"] == "activo" and latido["plan"] == plan and latido["tick_scheduler"] == "2026-10-26T08:01:00"
    assert latido["pid"] > 0
    assert not list(tmp_path.glob("*.tmp"))  # no queda el temporal del reemplazo atómico
