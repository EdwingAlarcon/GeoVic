@echo off
chcp 65001 >nul
REM Detiene el programador de GeoVictoria SIN tocar otros procesos.
REM Mata solo procesos (python y su ventana cmd) cuya linea de comandos contiene programador.py.
REM Uso: detener_programador.bat [nopause]   (nopause: para llamarlo desde otros scripts)
REM Reemplaza a detener_todas_instancias.bat (mataba TODOS los python.exe de la maquina).

cd /d "%~dp0.."

echo Buscando el programador...
powershell -NoProfile -Command "$f = { Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|cmd)(\.exe)?$' -and $_.CommandLine -match 'programador\.py' } }; $p = & $f; if (-not $p) { Write-Host '[INFO] No hay ningun programador en ejecucion.'; exit 0 }; foreach ($x in $p) { Stop-Process -Id $x.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('  detenido: ' + $x.Name + ' (PID ' + $x.ProcessId + ')') }; Start-Sleep -Seconds 2; if (& $f) { Write-Host '[WARN] Quedan procesos del programador (quiza de otro usuario: ejecuta como Administrador).'; exit 1 } else { Write-Host '[OK] Programador detenido.' }"
set "RC=%errorlevel%"

REM El lock solo guarda el PID (informativo); se limpia para no dejar un PID que ya no existe
if exist "src\logs\programador.lock" del /F /Q "src\logs\programador.lock" >nul 2>&1

echo.
if /I not "%~1"=="nopause" pause
exit /b %RC%
