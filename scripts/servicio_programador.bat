@echo off
REM Lanzador para la Tarea Programada de Windows (modo servidor, sin sesion interactiva).
REM - Fuerza navegador headless (no hay escritorio al arrancar tras un reinicio)
REM - Reinicia el programador si termina con error (ej: red aun no disponible)
REM No usar 'timeout' aqui: falla cuando la tarea corre sin consola; se usa ping como pausa.

cd /d "%~dp0.."

set GEOVICTORIA_HEADLESS=1
set PYTHONIOENCODING=utf-8

if not exist "src\logs" mkdir "src\logs"

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

:loop
echo [%date% %time%] Iniciando programador >> "src\logs\servicio.log"
%PYTHON% src\programador.py
set EXIT_CODE=%ERRORLEVEL%
echo [%date% %time%] Programador termino con codigo %EXIT_CODE% >> "src\logs\servicio.log"

REM Codigo 0 = parada limpia deliberada: no reiniciar
if %EXIT_CODE% EQU 0 exit /b 0

ping -n 61 127.0.0.1 >nul
goto loop
