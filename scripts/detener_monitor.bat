@echo off
chcp 65001 >nul
REM Detiene el monitor web (solo procesos cuya linea de comandos contiene monitor.py y su ventana cmd).
REM No toca el programador ni otros procesos. Uso: detener_monitor.bat [nopause]

cd /d "%~dp0.."

powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|cmd)(\.exe)?$' -and $_.CommandLine -match 'monitor\.py' }; if (-not $p) { Write-Host '[INFO] No hay ningun monitor en ejecucion.'; exit 0 }; foreach ($x in $p) { Stop-Process -Id $x.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('  detenido: ' + $x.Name + ' (PID ' + $x.ProcessId + ')') }; Write-Host '[OK] Monitor detenido.'"

echo.
if /I not "%~1"=="nopause" pause
exit /b 0
