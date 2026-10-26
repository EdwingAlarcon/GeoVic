@echo off
chcp 65001 >nul
title GeoVic - Marcar Salida Ahora

cd /d "%~dp0\.."

REM --- Detectar Python: venv si existe, sino sistema (el del sistema no suele tener playwright) ---
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
    echo [WARN] Entorno virtual no encontrado, usando Python del sistema
)

echo =========================================
echo  MARCANDO SALIDA para todos los empleados
echo =========================================
echo.

%PYTHON% scripts\marcar_forzado.py salida

echo.
pause
