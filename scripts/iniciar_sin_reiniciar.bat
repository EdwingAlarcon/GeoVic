@echo off
chcp 65001 >nul
echo ========================================
echo   INICIAR SISTEMA SIN REINICIAR
echo ========================================
echo.

cd /d "%~dp0\.."

REM --- Detectar Python: venv si existe, sino sistema ---
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo [OK] Usando Python del entorno virtual (.venv)
) else (
    set PYTHON=python
    echo [WARN] Usando Python del sistema
)
echo.

echo PASO 1: Verificando tareas programadas...
schtasks /Query /TN "GeoVictoria" 2>nul
if %errorlevel% equ 0 (
    echo [OK] Tarea GeoVictoria encontrada
) else (
    echo [INFO] Tarea GeoVictoria no encontrada
)
echo.

echo PASO 2: Deteniendo instancias anteriores...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *programador*" 2>nul
if %errorlevel% equ 0 (
    echo [OK] Instancias anteriores detenidas
    timeout /t 2 >nul
) else (
    echo [INFO] No habia instancias corriendo
)
echo.

echo PASO 3: Limpiando lock file...
if exist "src\logs\programador.lock" (
    del /F "src\logs\programador.lock"
    echo [OK] Lock file eliminado
) else (
    echo [INFO] No habia lock file
)
echo.

echo PASO 4: Iniciando programador...
echo.
echo Presione cualquier tecla para iniciar...
pause >nul

start "GeoVictoria Programador" /MIN %PYTHON% src\programador.py

echo.
echo ========================================
echo [OK] Programador iniciado en segundo plano
echo ========================================
echo.
echo Proximos pasos:
echo   1. Ver logs: src\logs\programador_[fecha].log
echo   2. Ver estado: scripts\ver_estado.bat
echo.
pause
