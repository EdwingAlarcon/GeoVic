@echo off
chcp 65001 >nul
REM Lo lanza el acceso directo de la carpeta Inicio de Windows (ver inicio_con_windows.bat) al iniciar sesion.
REM Espera 30 s a que el escritorio y la red esten listos y arranca programador y monitor:
REM sin ventanas si existe config\modo_oculto.flag, con ventanas si no. Si ya hay un programador, no duplica
REM (la instancia unica del programador lo impide).

cd /d "%~dp0.."
ping -n 31 127.0.0.1 >nul

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=%CD%\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

if exist "config\modo_oculto.flag" (
    call "%~dp0iniciar_oculto.bat" nopause
) else (
    start "Programador GeoVictoria" /D "%CD%" cmd /k ""%PYTHON%" src\programador.py"
    start "Monitor GeoVictoria" /D "%CD%" cmd /k ""%PYTHON%" scripts\monitor.py"
)
exit /b 0
