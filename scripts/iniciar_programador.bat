@echo off
chcp 65001 >nul
echo ================================================
echo   PROGRAMADOR DE MARCAJES GEOVICTORIA
echo   Configurado para Colombia
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

REM Verificar credenciales (.env o employees.json)
if not exist ".env" if not exist "config\employees.json" (
    echo ERROR: No se encontraron credenciales.
    echo Configure .env con GEOVICTORIA_USER y GEOVICTORIA_PASSWORD
    echo o cree config\employees.json con la lista de empleados.
    echo.
    pause
    exit /b 1
)

echo Iniciando programador...
echo Presione Ctrl+C para detener
echo.

%PYTHON% src\programador.py

pause
