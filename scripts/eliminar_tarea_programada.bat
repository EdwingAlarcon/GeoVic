@echo off
echo ========================================
echo   ELIMINAR TAREA PROGRAMADA
echo ========================================
echo.

echo ADVERTENCIA: Esto eliminara la configuracion
echo             de inicio automatico
echo.
echo ¿Continuar? (S/N):
choice /C SN /N
if errorlevel 2 goto :cancelar

echo.
echo Deteniendo programador...
taskkill /F /FI "WINDOWTITLE eq Programador GeoVictoria*" >nul 2>&1

echo Eliminando tarea programada...
schtasks /delete /tn "GeoVictoria Programador" /f >nul 2>&1

if %errorlevel%==0 (
    echo.
    echo [OK] Tarea eliminada correctamente
    echo.
    echo Para volver a configurarla:
    echo   scripts\configurar_tarea_windows.ps1
) else (
    echo.
    echo [INFO] No se encontro la tarea
)

goto :fin

:cancelar
echo.
echo Operacion cancelada

:fin
echo.
pause
