@echo off
chcp 65001 >nul
echo ================================================================================
echo   REINICIAR PROGRAMADOR CON CORRECCIONES
echo ================================================================================
echo.
echo Este script:
echo 1. Detiene cualquier instancia previa del programador
echo 2. Reinicia el programador con el codigo actualizado
echo.
pause

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
echo [1/3] Deteniendo instancias previas...
call "%~dp0detener_todas_instancias.bat"

echo.
echo [2/3] Esperando 3 segundos...
timeout /t 3 /nobreak >nul

echo.
echo [3/3] Iniciando programador actualizado...
start "GeoVictoria Programador" %PYTHON% src\programador.py

echo.
echo OK Programador reiniciado
echo.
echo Para verificar:
echo    - Revisa logs en src\logs\
echo    - Ejecuta: scripts\ver_estado.bat
echo.
pause
