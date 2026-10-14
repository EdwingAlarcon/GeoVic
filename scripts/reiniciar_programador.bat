@echo off
chcp 65001 >nul
REM Reinicia el programador a traves de la Tarea Programada "GeoVictoria Programador"
REM (instalada con instalar_tarea_servidor.bat). Usar despues de editar config\employees.json,
REM config\festivos_adicionales.json o actualizar el codigo: el programador solo lee esos
REM archivos al arrancar.
REM Requiere Administrador para detener/lanzar la tarea (se solicita automaticamente).

set "TASK=GeoVictoria Programador"

echo ============================================
echo   REINICIANDO PROGRAMADOR GEOVICTORIA
echo ============================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de Administrador...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0\.."

schtasks /query /tn "%TASK%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No existe la tarea "%TASK%".
    echo         Instalala primero con scripts\instalar_tarea_servidor.bat
    echo.
    pause
    exit /b 1
)

echo [1/4] Deteniendo la tarea...
schtasks /end /tn "%TASK%" >nul 2>&1

REM Por si quedo un programador.py fuera de la tarea (ej: lanzado a mano). Solo procesos
REM python cuya linea de comandos contiene programador.py; no toca otros python.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'programador\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
ping -n 4 127.0.0.1 >nul

echo [2/4] Limpiando lock obsoleto...
if exist "src\logs\programador.lock" (
    del /F "src\logs\programador.lock"
    echo       Lock eliminado
) else (
    echo       Sin lock
)

echo [3/4] Iniciando la tarea...
schtasks /run /tn "%TASK%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se pudo iniciar la tarea. Revisa el Programador de tareas (taskschd.msc).
    echo.
    pause
    exit /b 1
)
ping -n 8 127.0.0.1 >nul

echo [4/4] Verificando...
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'programador\.py' }; if ($p) { Write-Host ('[OK] Programador en ejecucion (PID ' + (($p | ForEach-Object ProcessId) -join ', ') + ')') } else { Write-Host '[WARN] No se detecta el proceso. Revisa src\logs\servicio.log y src\logs\programador_*.log'; exit 1 }"

echo.
echo ============================================
echo   Listo. Corre en segundo plano (sin ventana).
echo   Estado: scripts\ver_estado.bat
echo ============================================
pause
