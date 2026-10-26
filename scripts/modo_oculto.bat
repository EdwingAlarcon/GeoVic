@echo off
chcp 65001 >nul
REM Interruptor del MODO OCULTO: programador y monitor SIN consolas. El navegador sigue visible al marcar
REM (NO es headless: headless fallo con el portal real el 26-oct-2026 y no esta validado).
REM Cada ejecucion lo cambia: si esta apagado lo enciende y viceversa. Luego reinicia lo que esta corriendo.
REM Con el modo encendido, actualizar_servidor.bat y el arranque con Windows tambien arrancan sin consolas.
REM Se ve todo en http://127.0.0.1:8765 (botones para reiniciar/detener incluidos).

cd /d "%~dp0.."
set "FLAG=config\modo_oculto.flag"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=%CD%\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

if exist "%FLAG%" (
    del /F /Q "%FLAG%"
    echo Modo oculto DESACTIVADO. Reiniciando con ventanas...
    call "%~dp0detener_monitor.bat" nopause
    call "%~dp0reiniciar_programador.bat" nopause
    start "Monitor GeoVictoria" /D "%CD%" cmd /k ""%PYTHON%" scripts\monitor.py"
) else (
    >"%FLAG%" echo modo oculto
    echo Modo oculto ACTIVADO. Reiniciando sin ventanas...
    call "%~dp0iniciar_oculto.bat"
)
exit /b 0
