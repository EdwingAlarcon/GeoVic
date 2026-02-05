@echo off
echo ========================================
echo   EJECUTAR TAREA PROGRAMADA
echo ========================================
echo.

schtasks /run /tn "GeoVictoria Programador"

if %errorlevel%==0 (
    echo.
    echo [OK] Tarea iniciada correctamente
    echo.
    echo Se abrira una ventana con el programador
    echo Puedes MINIMIZARLA pero NO cerrarla
) else (
    echo.
    echo [ERROR] No se pudo iniciar la tarea
    echo.
    echo Posibles causas:
    echo   - La tarea no esta configurada
    echo   - Ejecutar: scripts\configurar_tarea_windows.ps1
)

echo.
pause
