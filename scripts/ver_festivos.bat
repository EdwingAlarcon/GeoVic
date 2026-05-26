@echo off
chcp 65001 >nul
echo ================================================
echo   FESTIVOS DE COLOMBIA
echo ================================================
echo.

cd /d "%~dp0\.."

REM --- Detectar Python: venv si existe, sino sistema ---
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

%PYTHON% src\festivos_colombia.py

echo.
pause
