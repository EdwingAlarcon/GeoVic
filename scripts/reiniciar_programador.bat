@echo off
chcp 65001 >nul
echo ============================================
echo   REINICIANDO PROGRAMADOR GEOVICTORIA
echo ============================================
echo.

cd /d "%~dp0\.."

REM --- Detectar Python: venv si existe, sino sistema ---
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo [OK] Usando Python del entorno virtual (.venv)
) else (
    set PYTHON=python
    echo [WARN] Entorno virtual no encontrado, usando Python del sistema
)
echo.

echo [1/3] Deteniendo programador actual...
taskkill /F /FI "WINDOWTITLE eq Programador GeoVictoria*" >nul 2>&1
taskkill /F /IM python.exe /FI "MEMUSAGE gt 10000" >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Limpiando lock file...
if exist "src\logs\programador.lock" (
    del /F "src\logs\programador.lock"
    echo       Lock eliminado
)
timeout /t 1 /nobreak >nul

echo [3/3] Iniciando programador...
echo.
start "Programador GeoVictoria" cmd /k "%PYTHON% src\programador.py"

echo.
echo ============================================
echo   PROGRAMADOR REINICIADO
echo   Se abrió una nueva ventana con el log
echo   Puedes cerrar esta ventana
echo ============================================
pause
