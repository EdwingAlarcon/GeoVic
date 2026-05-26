@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

REM --- Detectar Python: venv si existe, sino sistema ---
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

%PYTHON% scripts\verificar_estado.py
pause
