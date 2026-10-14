@echo off
chcp 65001 >nul

echo ================================================
echo   TAREA PROGRAMADA PARA SERVIDOR - GEOVICTORIA
echo   Arranca con Windows, sin iniciar sesion
echo   (Requiere permisos de Administrador)
echo ================================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de Administrador...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\" %*\"' -Verb RunAs"
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_tarea_servidor.ps1" %*
if errorlevel 1 (
    echo.
    echo ERROR: no se pudo crear la tarea. Revisa el mensaje anterior.
)
echo.
pause
