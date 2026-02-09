@echo off
chcp 65001 > nul
cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe scripts\diagnostico_sistema.py
) else (
    python scripts\diagnostico_sistema.py
)

