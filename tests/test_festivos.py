"""Tests para festivos_colombia.py — lógica de calendario colombiano."""
import sys
from pathlib import Path
from datetime import date

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.festivos_colombia import (
    cargar_festivos_adicionales,
    calcular_pascua,
    es_dia_laborable,
    es_festivo,
    obtener_festivos_colombia,
    siguiente_lunes,
)


# ---------------------------------------------------------------------------
# Festivos fijos (nunca cambian de fecha)
# ---------------------------------------------------------------------------

class TestFestivosFijos:
    def test_ano_nuevo(self):
        assert es_festivo(date(2026, 1, 1))

    def test_dia_del_trabajo(self):
        assert es_festivo(date(2026, 5, 1))

    def test_independencia(self):
        assert es_festivo(date(2026, 7, 20))

    def test_batalla_boyaca(self):
        assert es_festivo(date(2026, 8, 7))

    def test_inmaculada_concepcion(self):
        assert es_festivo(date(2026, 12, 8))

    def test_navidad(self):
        assert es_festivo(date(2026, 12, 25))

    def test_festivos_fijos_multiples_anos(self):
        for año in (2024, 2025, 2026, 2027):
            assert es_festivo(date(año, 12, 25)), f"Navidad {año} debe ser festivo"
            assert es_festivo(date(año, 1, 1)), f"Año nuevo {año} debe ser festivo"


# ---------------------------------------------------------------------------
# Domingos — siempre no laborables
# ---------------------------------------------------------------------------

class TestDomingos:
    def test_domingo_no_es_laborable(self):
        assert not es_dia_laborable(date(2026, 3, 1))  # Domingo

    def test_domingo_no_es_festivo_pero_tampoco_laborable(self):
        domingo = date(2026, 3, 8)
        assert domingo.weekday() == 6
        assert not es_dia_laborable(domingo)


# ---------------------------------------------------------------------------
# Días laborables ordinarios
# ---------------------------------------------------------------------------

class TestDiasLaborables:
    def test_lunes_ordinario(self):
        assert es_dia_laborable(date(2026, 3, 2))  # Lunes común

    def test_viernes_ordinario(self):
        assert es_dia_laborable(date(2026, 3, 6))  # Viernes común

    def test_sabado_ordinario_es_laborable(self):
        # Sábado no es festivo ni domingo → laborable según lógica
        assert es_dia_laborable(date(2026, 3, 7))

    def test_dia_ordinario_no_es_festivo(self):
        assert not es_festivo(date(2026, 3, 2))


# ---------------------------------------------------------------------------
# Algoritmo de Pascua (Meeus/Jones/Butcher)
# ---------------------------------------------------------------------------

class TestPascua:
    # Fechas de Pascua verificadas externamente
    PASCUAS_CONOCIDAS = {
        2024: date(2024, 3, 31),
        2025: date(2025, 4, 20),
        2026: date(2026, 4, 5),
        2027: date(2027, 3, 28),
        2028: date(2028, 4, 16),
    }

    def test_pascua_conocidas(self):
        for año, esperada in self.PASCUAS_CONOCIDAS.items():
            assert calcular_pascua(año) == esperada, f"Pascua {año} incorrecta"

    def test_jueves_santo_es_festivo(self):
        # Jueves Santo 2026: 2 abril (5 abril - 3 días)
        assert es_festivo(date(2026, 4, 2))

    def test_viernes_santo_es_festivo(self):
        # Viernes Santo 2026: 3 abril (5 abril - 2 días)
        assert es_festivo(date(2026, 4, 3))


# ---------------------------------------------------------------------------
# Ley Emiliani — festivos que se mueven al lunes
# ---------------------------------------------------------------------------

class TestLeyEmiliani:
    def test_siguiente_lunes_desde_lunes_no_mueve(self):
        lunes = date(2026, 3, 2)
        assert lunes.weekday() == 0
        assert siguiente_lunes(lunes) == lunes

    def test_siguiente_lunes_desde_martes(self):
        martes = date(2026, 3, 3)
        assert siguiente_lunes(martes) == date(2026, 3, 9)

    def test_siguiente_lunes_desde_sabado(self):
        sabado = date(2026, 3, 7)
        assert siguiente_lunes(sabado) == date(2026, 3, 9)

    def test_reyes_magos_movido_a_lunes(self):
        # 6 enero 2026 es martes → se mueve al 12 enero
        reyes = date(2026, 1, 6)
        assert reyes.weekday() == 1  # martes
        lunes = siguiente_lunes(reyes)
        assert lunes == date(2026, 1, 12)
        assert es_festivo(lunes)
        assert not es_festivo(reyes)  # la fecha original NO es festivo


# ---------------------------------------------------------------------------
# Conteo total de festivos por año
# ---------------------------------------------------------------------------

class TestConteoFestivos:
    def test_colombia_tiene_18_festivos_legales_mas_adicionales(self):
        for año in (2024, 2025, 2026):
            festivos = obtener_festivos_colombia(año)
            esperados = 18 + len(cargar_festivos_adicionales(año))
            assert len(festivos) == esperados, f"Año {año}: esperados {esperados}, got {len(festivos)}"

    def test_festivos_ordenados(self):
        festivos = obtener_festivos_colombia(2026)
        assert festivos == sorted(festivos)

    def test_sin_fechas_duplicadas(self):
        festivos = obtener_festivos_colombia(2026)
        assert len(festivos) == len(set(festivos))
