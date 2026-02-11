@echo off
echo ========================================
echo INICIAR SISTEMA SIN REINICIAR
echo ========================================
echo.

cd /d "%~dp0\.."

echo PASO 1: Verificando tareas programadas...
echo ========================================
schtasks /Query /TN "GeoVictoria" 2>nul
if %errorlevel% equ 0 (
    echo [OK] Tarea "GeoVictoria" encontrada
) else (
    echo [ADVERTENCIA] Tarea "GeoVictoria" no encontrada
)
echo.

echo PASO 2: Deteniendo instancias anteriores...
echo ========================================
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *programador*" 2>nul
if %errorlevel% equ 0 (
    echo [OK] Instancias anteriores detenidas
    timeout /t 2 >nul
) else (
    echo [INFO] No habia instancias corriendo
)
echo.

echo PASO 3: Limpiando lock file...
echo ========================================
if exist "src\logs\programador.lock" (
    del /F "src\logs\programador.lock"
    echo [OK] Lock file eliminado
) else (
    echo [INFO] No habia lock file
)
echo.

echo PASO 4: Iniciando programador...
echo ========================================
echo.
echo El programador se iniciara en una nueva ventana.
echo NO CIERRE esta ventana - se ejecutara en segundo plano.
echo.
echo Para verificar que funciona, revise:
echo   - src\logs\programador_[fecha].log
echo   - Deberia ver mensajes cada hora
echo.
echo Presione cualquier tecla para iniciar...
pause >nul

start "GeoVictoria Programador" /MIN python src\programador.py

echo.
echo ========================================
echo [OK] Programador iniciado en segundo plano
echo ========================================
echo.
echo Proximos pasos:
echo 1. Verificar logs en: src\logs\programador_[fecha].log
echo 2. Ejecutar diagnostico: scripts\diagnostico_estado.bat
echo.
pause
