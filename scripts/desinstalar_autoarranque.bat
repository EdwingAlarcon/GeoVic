@echo off
chcp 65001 >nul

set "TASK=GeoVictoria Programador"

echo.
echo ================================================
echo   DESINSTALAR ARRANQUE AUTOMATICO
echo ================================================
echo.

REM Detener el programador si esta corriendo
taskkill /F /FI "WINDOWTITLE eq GeoVictoria Programador" >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

REM Eliminar la tarea del Programador de tareas
schtasks /delete /tn "%TASK%" /f >nul 2>&1

if errorlevel 1 (
    echo No se encontro la tarea o ya estaba eliminada.
) else (
    echo [OK] Tarea eliminada: %TASK%
    echo [OK] El programador ya no iniciara automaticamente.
)

echo.
pause
