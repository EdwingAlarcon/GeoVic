@echo off
echo ========================================
echo   CONFIGURAR TAREA PROGRAMADA
echo   (Requiere permisos de Administrador)
echo ========================================
echo.

REM Verificar si se esta ejecutando como administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] Este script requiere permisos de Administrador
    echo.
    echo Soluciones:
    echo   1. Clic derecho en este archivo ^> "Ejecutar como administrador"
    echo   2. O continuar manualmente (se abrira ventana de permisos^)
    echo.
    pause
    
    REM Intentar elevar permisos
    powershell -Command "Start-Process PowerShell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0configurar_tarea_windows.ps1\"' -Verb RunAs"
    exit /b
)

REM Si ya tiene permisos, ejecutar directamente
powershell -ExecutionPolicy Bypass -File "%~dp0configurar_tarea_windows.ps1"
pause
