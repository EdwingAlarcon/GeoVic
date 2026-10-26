@echo off
chcp 65001 >nul
REM Interruptor del ARRANQUE CON WINDOWS: crea o borra un acceso directo en la carpeta Inicio del usuario.
REM Cada ejecucion lo cambia. Al iniciar sesion tras un reinicio del servidor arranca programador y monitor
REM (scripts\iniciar_al_inicio.bat). No usa Tareas Programadas ni pide Administrador.
REM Limite: Windows solo ejecuta la carpeta Inicio cuando ESE usuario inicia sesion; si el servidor no
REM inicia sesion solo tras reiniciar, hay que entrar una vez (RDP o consola) para que arranque.

cd /d "%~dp0.."
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\GeoVictoria.lnk"

if exist "%LNK%" (
    del /F /Q "%LNK%"
    echo Arranque con Windows DESACTIVADO ^(acceso directo eliminado^).
) else (
    powershell -NoProfile -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%'); $s.TargetPath = '%~dp0iniciar_al_inicio.bat'; $s.WorkingDirectory = '%CD%'; $s.WindowStyle = 7; $s.Save()"
    if exist "%LNK%" (
        echo Arranque con Windows ACTIVADO: al iniciar sesion arrancan programador y monitor.
    ) else (
        echo [ERROR] No se pudo crear el acceso directo en la carpeta Inicio.
    )
)
echo.
pause
exit /b 0
