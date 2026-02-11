@echo off
echo ========================================
echo Habilitando Tareas Programadas GeoVic
echo ========================================
echo.
echo REQUIERE PERMISOS DE ADMINISTRADOR
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Este script requiere permisos de administrador
    echo Por favor, ejecute como Administrador ^(clic derecho - Ejecutar como administrador^)
    pause
    exit /b 1
)

echo Habilitando tarea "GeoVictoria"...
schtasks /Change /TN "GeoVictoria" /Enable
if %errorlevel% equ 0 (
    echo [OK] Tarea "GeoVictoria" habilitada
) else (
    echo [ERROR] No se pudo habilitar "GeoVictoria"
)

echo.
echo Habilitando tarea "GeoVictoria Marcajes Automaticos"...
schtasks /Change /TN "GeoVictoria Marcajes Automaticos" /Enable
if %errorlevel% equ 0 (
    echo [OK] Tarea "GeoVictoria Marcajes Automaticos" habilitada
) else (
    echo [ERROR] No se pudo habilitar "GeoVictoria Marcajes Automaticos"
)

echo.
echo ========================================
echo Verificando estado de las tareas...
echo ========================================
schtasks /Query /TN "GeoVictoria" /FO LIST
echo.
schtasks /Query /TN "GeoVictoria Marcajes Automaticos" /FO LIST

echo.
echo ========================================
echo COMPLETADO
echo ========================================
pause
