@echo off
echo ========================================
echo   DETENER TAREA PROGRAMADA
echo ========================================
echo.

echo Deteniendo procesos del programador...
taskkill /F /FI "WINDOWTITLE eq Programador GeoVictoria*" >nul 2>&1

echo.
echo [OK] Programador detenido
echo.
echo NOTA: La tarea seguira configurada en Windows
echo       Se volvera a ejecutar al reiniciar sesion
echo.
pause
