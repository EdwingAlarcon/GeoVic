# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- `iniciar_programador.bat` — start the scheduler (window "Programador GeoVictoria")
- `reiniciar_programador.bat` / `detener_programador.bat` — restart / stop it; they kill only `programador.py` processes, never other Python
- `iniciar_oculto.bat` / `detener_monitor.bat` — run scheduler + monitor with hidden consoles; the browser stays visible while marking (it clears `GEOVICTORIA_HEADLESS` on purpose: see Key Constraints); stops what is running first, so it also restarts
- `ejecutar_manual.bat` — one-off marking
- `ver_estado.bat` — show current scheduler state (calls `scripts/verificar_estado.py`)
- `diagnostico_sistema.bat` — scheduler instances, lock, registry, recent logs and today's alerts per user
- `probar_login.bat [id|name]` — test ONE employee's login without marking (works for disabled employees too) and explain the failure (bad credentials, locked account, password change, 2FA…); logic lives in `src/diagnostico_login.py`
- `ver_log_en_vivo.bat` — follow the scheduler log live (the monitor page also has a "Log en vivo" panel with usernames and passwords censored, so this window is optional)
- `monitor.bat` — live web monitor (`http://127.0.0.1:8765`): per-employee status, scheduler heartbeat, instance count, alerts, "Log en vivo" panel, Reiniciar/Detener/Iniciar buttons for the scheduler, and "Marcar pendientes" (lists who is VENCIDA/NO confirmada; launches `scripts/marcar_pendientes.py emp:accion…`, which only clicks if the portal offers that button, skips anyone another process is handling, and confirms with a second login). Logic in `src/estado_monitor.py` (pure, tested); server in `scripts/monitor.py`; process control in `src/control_programador.py`. Never serves credentials. The only acting route is `POST /api/accion`: loopback clients only, custom header `X-GeoVic-Accion`, token if set, and it refuses restart/stop near a marking (`bloqueo_por_marcaje`) unless forced
- `modo_oculto.bat` / `inicio_con_windows.bat` — toggles: hidden consoles mode, not headless (`config/modo_oculto.flag`, honored by `actualizar_servidor.bat` and `iniciar_al_inicio.bat`) and a Startup-folder shortcut that launches everything at logon (no Scheduled Task, no admin; only fires when that user logs on)
- `actualizar_servidor.bat` (project root) — update an installed server from the extracted zip

## Architecture

### Source Modules (`src/`)

**`geovictoria.py`** — Core browser automation layer. Key functions:
- `run(accion_esperada, empleado)` — Opens Chromium, logs in, clicks the available marking button. If `accion_esperada` is set ("Entrada"/"Salida"), validates that the expected button matches before clicking.
- `verificar_estado(empleado)` — Same login flow but only checks which button is visible, without clicking. Used by the scheduler to sync state.
- `Config` class — Tune timeouts and headless mode here; `HEADLESS = False` keeps the browser visible. `MAX_NAVEGADORES` (env `GEOVICTORIA_MAX_NAVEGADORES`, default 3) caps simultaneous Chromium instances: extra jobs wait for a slot instead of failing login under load. `LOGIN_TIMEOUT` is 25 s.
- CSS selectors are loaded from `config/selectors.json` at import time (falls back to hardcoded defaults if file is missing).

**`programador.py`** — APScheduler-based scheduler. Key behaviors:
- Uses `BlockingScheduler` with `CronTrigger` in `America/Bogota` timezone.
- Schedules 4–5 jobs per employee: entrada L-V, salida L-V, entrada sábado, salida sábado, plus an hourly `verificar_pendientes_emp` that catches missed markings (e.g., PC started late).
- Enforces a **single instance per machine** via `src/control_concurrencia.py` (named Windows mutex; `flock` on POSIX). Deleting the lock file does not allow a second instance, and the exclusion is released automatically if the process dies, so no manual cleanup is needed after a crash or reboot. A second launch exits with "Programador ya en ejecución". `src/logs/programador.lock` only holds the PID, for information.
- The thread pool has 20 workers and jobs get `misfire_grace_time=300`, so jobs waiting for a browser slot are not dropped as missed.
- **Independent confirmation**: after every successful marking it schedules `confirmar_marcaje_emp` (~90 s later, `GEOVICTORIA_CONFIRMAR_DEMORA`), which logs in a second time and checks that the portal no longer offers that action's button (`confirmacion_de`). If the portal still offers it, it writes an alert ("NO CONFIRMADO por el portal"). `GEOVICTORIA_CONFIRMAR=0` disables it.
- **Safe retry**: when the portal still offers the button (confirmation `False`, or `run()` could not confirm its own click), the local record is voided (`anular_registro`: `ejecutado: false` + `anulado`) and `_programar_reintento` schedules up to `GEOVICTORIA_REINTENTOS` retries (default 2; `0` disables) every `GEOVICTORIA_REINTENTO_DEMORA` s (default 180), only between 30 min before and 120 min after the scheduled time (`src/reintentos.py`, pure, tested). `reintentar_marcaje_emp` calls `run(accion_esperada=…)`, which only clicks if the portal offers that exact button, so it cannot duplicate: the **portal is the truth, not the local record**. The alert is written only when retries are exhausted. A void record no longer counts for the cooldown or for the monitor. The confirmation is an in-memory job, so on startup `_reconciliar_confirmaciones` re-schedules it (staggered 10 s) for today's marks made by the scheduler that have no conclusive confirmation event (`marcajes_sin_confirmar`): restarts no longer lose it.
- **Heartbeat**: a thread writes `src/logs/latido.json` every 20 s (process alive) and an interval job updates `tick_scheduler` (scheduler responding), plus the real scheduled times (`plan`). `src/bitacora.py` appends structured events (login, marcaje, registro, confirmacion, alerta…) to `eventos_YYYYMMDD.jsonl`; recording never raises and never stores credentials.
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
- `eventos_YYYYMMDD.jsonl` — structured event journal (one JSON per line, fsync'd); source of truth for the monitor. `latido.json` — heartbeat + today's real schedule. Each mark in `registro_{emp_id}.json` carries `"origen"`: `"programador"` (it clicked) or `"portal"` (already done, detected from the portal).
- `programador.lock` — PID of the running scheduler (informational). Stale locks are harmless: the real single-instance guard is the OS-level lock.

### Key Constraints

- `apscheduler` is pinned to `<4.0` due to a breaking API change in v4.
- The scheduler is **not async**; it calls `asyncio.run(...)` inside sync job functions (APScheduler's `BlockingScheduler` is synchronous). Do not mix with async schedulers.
- `HEADLESS = False` is the default — the browser window is visible. **Do not enable headless in production** (`GEOVICTORIA_HEADLESS`): on 2026-10-26 the clicks of the first 3 real salidas made in headless were not saved by the live portal (it kept offering "Salida"), so it is not validated. The scheduler logs a warning and an `aviso` event when it is on. Hiding the consoles (`modo_oculto.bat`) is fine; hiding the browser is not. Any future headless test must be controlled (one employee, watched, with the monitor) and never done on everyone's real markings.
- All times are in `America/Bogota` (Colombia, UTC-5, no DST).
