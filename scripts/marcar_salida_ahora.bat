@echo off
chcp 65001 >nul
title GeoVic - Marcar Salida Ahora

set SCRIPT_DIR=%~dp0
set REPO_DIR=%SCRIPT_DIR%..

echo =========================================
echo  MARCANDO SALIDA para todos los empleados
echo =========================================
echo.

python "%REPO_DIR%\scripts\marcar_forzado.py" salida

echo.
pause
