@echo off
chcp 65001 >nul
echo ================================================
echo   MARCAJE MANUAL GEOVICTORIA
echo ================================================
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

REM Verificar credenciales
if not exist ".env" if not exist "config\employees.json" (
    echo ERROR: No se encontraron credenciales.
    echo Configure .env o cree config\employees.json
    echo.
    pause
    exit /b 1
)

echo Ejecutando marcaje manual...
echo.

%PYTHON% src\geovictoria.py

echo.
echo ================================================
pause
