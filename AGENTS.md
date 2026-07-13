# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

GeoVic is a Python automation system that performs attendance check-in/check-out on the GeoVictoria portal (`clients.geovictoria.com`) using Playwright browser automation. It supports multiple employees, respects Colombia's holiday calendar, and runs as a long-lived scheduler process.

## Setup & Commands

```bash
# Install dependencies (Python 3.8+ required)
pip install -r requirements.txt
playwright install chromium

# Configure credentials
cp .env.example .env          # then edit .env with real credentials
# OR: copy config/employees.example.json → config/employees.json for multi-employee

# Run a one-off manual marking (uses current available button)
python src/geovictoria.py

# Start the automatic scheduler (blocking, long-lived process)
python src/programador.py

# View Colombia holidays for the current year
python src/festivos_colombia.py

# Run all tests
pytest

# Run a specific test file
pytest tests/test_festivos.py
pytest tests/test_empleados.py
```

**Windows convenience scripts** (in `scripts/`):
- `iniciar_programador.bat` — start the scheduler
- `ejecutar_manual.bat` — one-off marking
- `ver_estado.bat` — show current scheduler state (calls `scripts/verificar_estado.py`)
- `corregir_problema_completo.bat` — stop all instances, clean corrupt registry, re-diagnose

## Architecture

### Source Modules (`src/`)

**`geovictoria.py`** — Core browser automation layer. Key functions:
- `run(accion_esperada, empleado)` — Opens Chromium, logs in, clicks the available marking button. If `accion_esperada` is set ("Entrada"/"Salida"), validates that the expected button matches before clicking.
- `verificar_estado(empleado)` — Same login flow but only checks which button is visible, without clicking. Used by the scheduler to sync state.
- `Config` class — Tune timeouts and headless mode here; `HEADLESS = False` keeps the browser visible.
- CSS selectors are loaded from `config/selectors.json` at import time (falls back to hardcoded defaults if file is missing).

**`programador.py`** — APScheduler-based scheduler. Key behaviors:
- Uses `BlockingScheduler` with `CronTrigger` in `America/Bogota` timezone.
- Schedules 4–5 jobs per employee: entrada L-V, salida L-V, entrada sábado, salida sábado, plus an hourly `verificar_pendientes_emp` that catches missed markings (e.g., PC started late).
- Uses a **lock file** (`src/logs/programador.lock`) to prevent multiple instances. If the process is hard-killed, delete the lock file manually before restarting.
- Salida jobs check that the corresponding entrada was already registered; if not, they call `verificar_estado` to detect entries made outside the scheduler (manual or via portal).
- `HorarioConfig.COOLDOWN_ENTRE_MARCAJES = 300` — minimum seconds between two markings for the same employee.
- Validation window for scheduled jobs: ±30 minutes around the configured time; markings outside that window are skipped.

**`empleados.py`** — Configuration loader. Priority:
1. **Multi-employee**: `config/employees.json` — list of employee dicts with `id`, `nombre`, `usuario`, `password`, `activo`, `horario`.
2. **Single-employee fallback**: `GEOVICTORIA_USER` / `GEOVICTORIA_PASSWORD` environment variables (from `.env`).
- Missing `horario` fields are filled with defaults (Mon-Fri 7:00/17:00, Saturday 7:00/13:00, `trabaja_sabados: true`).
- Set `"activo": false` in the JSON to disable an employee without removing the entry.

**`festivos_colombia.py`** — Holiday calendar. Uses the Meeus/Jones/Butcher algorithm for Easter and applies Ley Emiliani (moveable feasts shift to the next Monday). Computes 18 legal holidays per year automatically; no manual updates needed for those. Additionally loads `config/festivos_adicionales.json` (via `cargar_festivos_adicionales`) to support one-off holidays decreed outside the standard legal calendar — edit that JSON and restart `programador.py` to pick up new entries.

**`cache_estado.py`** — Thread-safe in-memory cache (60 s TTL) for the portal button state, keyed per employee (`estado_{emp_id}`). Avoids redundant browser sessions when multiple jobs check state in quick succession. Call `cache.invalidar(key)` before any marking to ensure a fresh read.

### Configuration Files (`config/`)

- **`employees.json`** (gitignored, create from `employees.example.json`) — per-employee credentials and schedule overrides.
- **`selectors.json`** — CSS selectors for the GeoVictoria portal login form and attendance buttons. **Update this file if the portal changes its DOM** instead of modifying `geovictoria.py`.
- **`festivos_adicionales.json`** (tracked in git) — list of `{"fecha": "YYYY-MM-DD", "nombre": "..."}` entries for holidays decreed outside Colombia's standard legal calendar (e.g. a special one-off holiday). Loaded by `festivos_colombia.py` and merged into `obtener_festivos_colombia()`. The scheduler checks `es_festivo(hoy)` before every marking (`programador.py`), so a date listed here is skipped the same way as a normal holiday — but the running `programador.py` process must be restarted after editing this file for the change to take effect.

### Logs & State (`src/logs/`)

- `geovictoria_YYYYMMDD.log` — per-day browser automation log (rotating, 5 MB × 5 files).
- `programador_YYYYMMDD.log` — scheduler event log.
- `registro_{emp_id}.json` / `registro_ejecuciones.json` — JSON registry tracking which markings were executed today (last 30 days). Used to prevent double-markings.
- `alertas.log` — append-only file written when a marking fails; useful for external monitoring.
- `programador.lock` — PID file. Delete manually if the scheduler crashed without cleanup.

### Key Constraints

- `apscheduler` is pinned to `<4.0` due to a breaking API change in v4.
- The scheduler is **not async**; it calls `asyncio.run(...)` inside sync job functions (APScheduler's `BlockingScheduler` is synchronous). Do not mix with async schedulers.
- `HEADLESS = False` is the default — the browser window is visible. Change to `True` in `Config` for unattended/server environments.
- All times are in `America/Bogota` (Colombia, UTC-5, no DST).
