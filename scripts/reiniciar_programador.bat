@echo off
chcp 65001 >nul
REM Reinicia el programador: lo detiene (solo procesos de programador.py) y lo lanza de nuevo
REM en una ventana "Programador GeoVictoria". Usalo despues de editar config\employees.json
REM o config\festivos_adicionales.json: el programador solo lee esos archivos al arrancar.
echo ============================================
echo   REINICIANDO PROGRAMADOR GEOVICTORIA
echo ============================================
echo.

cd /d "%~dp0\.."

REM --- Detectar Python: venv si existe, sino sistema ---
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
    echo [OK] Usando Python del entorno virtual (.venv)
) else (
    set "PYTHON=python"
    echo [WARN] Entorno virtual no encontrado, usando Python del sistema
)
echo.

echo [1/3] Deteniendo programador actual...
call "%~dp0detener_programador.bat" nopause
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo detener el programador anterior. No se inicia uno nuevo:
    echo         saldria con "ya en ejecucion" y seguiria el viejo con la configuracion antigua.
    echo.
    pause
    exit /b 1
)

echo [2/3] Iniciando programador...
start "Programador GeoVictoria" cmd /k "%PYTHON% src\programador.py"
ping -n 8 127.0.0.1 >nul

echo [3/3] Verificando...
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw)(\.exe)?$' -and $_.CommandLine -match 'programador\.py' }; if ($p) { Write-Host '[OK] Programador en ejecucion.' } else { Write-Host '[WARN] No se detecta el proceso. Mira la ventana Programador GeoVictoria.'; exit 1 }"

echo.
echo ============================================
echo   PROGRAMADOR REINICIADO
echo   Deja abierta la ventana "Programador GeoVictoria"
echo   (puedes minimizarla, no cerrarla)
echo ============================================
pause
