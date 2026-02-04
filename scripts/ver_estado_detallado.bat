@echo off
REM Script para verificar estado de marcajes
cd /d "%~dp0\.."
python scripts\verificar_estado.py
pause
