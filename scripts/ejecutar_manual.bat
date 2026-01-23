@echo off
REM Script para ejecutar un marcaje manual único
REM Útil para pruebas o marcajes ocasionales

echo ================================================
echo   MARCAJE MANUAL GEOVICTORIA
echo ================================================
echo.

cd /d "%~dp0\.."

REM Verificar que existe el archivo .env
if not exist ".env" (
    echo ERROR: Archivo .env no encontrado
    echo Por favor configure sus credenciales primero
    echo.
    pause
    exit /b 1
)

REM Ejecutar marcaje único
echo Ejecutando marcaje manual...
echo.

python src\geovictoria.py

echo.
echo ================================================
pause
