@echo off
chcp 65001 >nul
REM Detiene el programador que corre via la Tarea Programada "GeoVictoria Programador".
REM La tarea sigue instalada: volvera a arrancar con el proximo reinicio del servidor
REM o con scripts\ejecutar_tarea_programada.bat.
REM Requiere Administrador (se solicita automaticamente).

set "TASK=GeoVictoria Programador"

echo ========================================
echo   DETENER PROGRAMADOR GEOVICTORIA
echo ========================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de Administrador...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0\.."

echo [1/3] Deteniendo la tarea...
schtasks /end /tn "%TASK%" >nul 2>&1

REM Tambien cualquier programador.py lanzado fuera de la tarea. Solo procesos python cuya
REM linea de comandos contiene programador.py; no toca otros python.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'programador\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
ping -n 4 127.0.0.1 >nul

echo [2/3] Limpiando lock...
if exist "src\logs\programador.lock" (
    del /F "src\logs\programador.lock"
    echo       Lock eliminado
) else (
    echo       Sin lock
)

echo [3/3] Verificando...
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'programador\.py' }; if ($p) { Write-Host ('[WARN] Aun hay un programador.py en ejecucion (PID ' + (($p | ForEach-Object ProcessId) -join ', ') + ')'); exit 1 } else { Write-Host '[OK] Programador detenido' }"

echo.
echo NOTA: la tarea sigue instalada. Arrancara de nuevo al reiniciar el servidor.
echo       Para evitarlo hasta nuevo aviso: schtasks /change /tn "%TASK%" /disable
echo       (y /enable para reactivarla). Para quitarla: scripts\eliminar_tarea_programada.bat
echo.
pause
