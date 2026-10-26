@echo off
chcp 65001 >nul
REM Inicia programador y monitor SIN ventanas (consolas ocultas) y con el navegador en modo headless.
REM Se ve todo desde el monitor: http://127.0.0.1:8765 (incluye el panel "Log en vivo").
REM Detiene antes lo que haya (programador y monitor), asi que sirve tambien para reiniciar.
REM
REM Para volver al modo con ventanas: reiniciar_programador.bat  (y monitor.bat si lo quieres)
REM Para detenerlo todo: detener_programador.bat y detener_monitor.bat
REM
REM Antes de fiarte de este modo en produccion, confirma un marcaje REAL en headless (ver el monitor:
REM debe quedar "Confirmada"). Si el portal no acepta el navegador sin ventana, el monitor lo marca
REM "NO confirmada" y vuelves al modo con ventanas.

cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=%CD%\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
    echo [WARN] Entorno virtual no encontrado, usando Python del sistema
)

echo [1/3] Deteniendo lo que haya en marcha...
call "%~dp0detener_programador.bat" nopause
if errorlevel 1 (
    echo [ERROR] No se pudo detener el programador anterior. No se inicia otro.
    pause
    exit /b 1
)
call "%~dp0detener_monitor.bat" nopause

echo [2/3] Iniciando programador y monitor ocultos (headless)...
set "GEOVICTORIA_HEADLESS=1"
powershell -NoProfile -Command "Start-Process -FilePath '%PYTHON%' -ArgumentList 'src\programador.py' -WorkingDirectory '%CD%' -WindowStyle Hidden; Start-Process -FilePath '%PYTHON%' -ArgumentList 'scripts\monitor.py' -WorkingDirectory '%CD%' -WindowStyle Hidden"
ping -n 10 127.0.0.1 >nul

echo [3/3] Verificando...
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw)(\.exe)?$' }; $a = $p | Where-Object { $_.CommandLine -match 'programador\.py' }; $m = $p | Where-Object { $_.CommandLine -match 'monitor\.py' }; if ($a) { Write-Host '[OK] Programador oculto en ejecucion.' } else { Write-Host '[ERROR] No se detecta el programador.' }; if ($m) { Write-Host '[OK] Monitor oculto: http://127.0.0.1:8765' } else { Write-Host '[AVISO] No se detecta el monitor.' }; if (-not $a) { exit 1 }"
set "RC=%errorlevel%"

echo.
if "%RC%"=="0" (
    echo Listo. No hay ventanas: abre http://127.0.0.1:8765 para ver el estado.
) else (
    echo El programador no arranco: usa reiniciar_programador.bat para verlo con ventana y leer el error.
)
if /I not "%~1"=="nopause" pause
exit /b %RC%
