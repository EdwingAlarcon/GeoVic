@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo.
echo ================================================
echo   ARRANQUE AUTOMATICO - GEOVICTORIA
echo   Configura inicio automatico con Windows
echo ================================================
echo.
echo El programador se iniciara solo al iniciar sesion.
echo No quedara ninguna ventana de consola visible.
echo Los marcajes se registran en src\logs\
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_autoarranque.ps1"

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo crear la tarea.
    echo Intenta hacer click derecho en este archivo y elegir
    echo "Ejecutar como administrador".
    echo.
    pause
    exit /b 1
)

echo Iniciando el programador ahora mismo...
start /B "" "%CD%\.venv\Scripts\pythonw.exe" src\programador.py

echo [OK] Programador iniciado en segundo plano.
echo.
pause
