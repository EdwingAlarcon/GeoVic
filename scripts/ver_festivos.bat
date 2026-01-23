@echo off
REM Script para ver los festivos de Colombia del año actual

echo ================================================
echo   FESTIVOS DE COLOMBIA
echo ================================================
echo.

cd /d "%~dp0\.."

python src\festivos_colombia.py

echo.
pause
