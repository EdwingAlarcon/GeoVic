@echo off
REM Script para ejecutar el programador de marcajes GeoVictoria
REM Este archivo mantiene el programador corriendo en segundo plano

echo ================================================
echo   PROGRAMADOR DE MARCAJES GEOVICTORIA
echo   Configurado para Colombia
echo ================================================
echo.

cd /d "%~dp0"

REM Verificar que existe el archivo .env
if not exist "..\.env" (
    echo ERROR: Archivo .env no encontrado
    echo Por favor configure sus credenciales primero
    echo.
    pause
    exit /b 1
)

REM Ejecutar el programador
echo Iniciando programador...
echo Presione Ctrl+C para detener
echo.

python src\programador.py

pause
