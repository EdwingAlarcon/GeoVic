@echo off
echo ========================================
echo DIAGNOSTICO DEL SISTEMA DE MARCAJES
echo ========================================
echo.
echo Verificando estado actual del sistema...
echo.

cd /d "%~dp0\.."

python scripts\diagnostico_estado_completo.py

echo.
echo ========================================
echo Presione cualquier tecla para salir...
pause >nul
