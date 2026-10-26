@echo off
chcp 65001 >nul
REM Prueba el login de UN empleado en GeoVictoria, sin marcar, y explica por que falla.
REM Uso: probar_login.bat            (lista los empleados y pregunta cual)
REM      probar_login.bat emp15      (por id o por parte del nombre)

cd /d "%~dp0.."

REM --- Detectar Python: venv si existe, sino sistema ---
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
    echo [WARN] Entorno virtual no encontrado, usando Python del sistema
)

echo ================================================
echo   PROBAR LOGIN DE UN EMPLEADO (no marca nada)
echo ================================================

%PYTHON% scripts\probar_login.py %*

echo.
pause
