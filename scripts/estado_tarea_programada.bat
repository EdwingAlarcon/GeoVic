@echo off
echo ========================================
echo   ESTADO TAREA PROGRAMADA
echo ========================================
echo.

schtasks /query /tn "GeoVictoria Programador" /fo list /v 2>nul

if %errorlevel%==0 (
    echo.
    echo ========================================
    echo Para administrar:
    echo   - Ejecutar: taskschd.msc
    echo   - Buscar: GeoVictoria Programador
    echo ========================================
) else (
    echo [INFO] No existe tarea programada configurada
    echo.
    echo Para configurarla:
    echo   scripts\configurar_tarea_windows.ps1
)

echo.
pause
