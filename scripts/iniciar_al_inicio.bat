@echo off
chcp 65001 >nul
REM Lo lanza el acceso directo de la carpeta Inicio de Windows (ver inicio_con_windows.bat) al iniciar sesion.
REM Espera 30 s a que el escritorio y la red esten listos y arranca programador y monitor en ventanas
REM (navegador visible) y abre la pagina del monitor. Si ya hay un programador, no duplica
REM (la instancia unica del programador lo impide).

cd /d "%~dp0.."
ping -n 31 127.0.0.1 >nul

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=%CD%\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

start "Programador GeoVictoria" /D "%CD%" cmd /k ""%PYTHON%" src\programador.py"
start "Monitor GeoVictoria" /D "%CD%" cmd /k ""%PYTHON%" scripts\monitor.py --abrir"
exit /b 0
