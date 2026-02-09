@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║     CORRECCIÓN COMPLETA DE MARCAJES DUPLICADOS                 ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo Este script ejecutará TODOS los pasos necesarios para corregir
echo el problema de marcajes duplicados.
echo.
pause

echo.
echo ════════════════════════════════════════════════════════════════
echo  PASO 1: Instalando dependencias...
echo ════════════════════════════════════════════════════════════════
echo.
call scripts\instalar_psutil.bat

echo.
echo ════════════════════════════════════════════════════════════════
echo  PASO 2: Deteniendo todas las instancias del programador...
echo ════════════════════════════════════════════════════════════════
echo.

echo Buscando procesos de Python...
tasklist /FI "IMAGENAME eq python.exe" /V 2>nul | findstr /I "programador" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ Procesos encontrados - Deteniendo...
    for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /NH ^| findstr /I "python"') do (
        echo   • Deteniendo PID %%i...
        taskkill /PID %%i /F >nul 2>&1
    )
) else (
    echo ℹ No se encontraron procesos del programador
)

echo.
echo Eliminando archivo de lock...
if exist "src\logs\programador.lock" (
    del /F "src\logs\programador.lock" 2>nul
    echo ✓ Lock file eliminado
) else (
    echo ℹ Lock file no encontrado
)

timeout /t 2 >nul

echo.
echo ════════════════════════════════════════════════════════════════
echo  PASO 3: Limpiando registro de ejecuciones de hoy...
echo ════════════════════════════════════════════════════════════════
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe scripts\limpiar_registro_hoy.py --auto
) else (
    python scripts\limpiar_registro_hoy.py --auto
)

echo.
echo ════════════════════════════════════════════════════════════════
echo  PASO 4: Ejecutando diagnóstico del sistema...
echo ════════════════════════════════════════════════════════════════
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe scripts\diagnostico_sistema.py
) else (
    python scripts\diagnostico_sistema.py
)

echo.
echo ════════════════════════════════════════════════════════════════
echo  CORRECCIÓN COMPLETADA
echo ════════════════════════════════════════════════════════════════
echo.
echo ✅ Todos los pasos ejecutados correctamente
echo.
echo 📋 PRÓXIMOS PASOS MANUALES:
echo.
echo    1. Ejecute: scripts\iniciar_programador.bat
echo       (para iniciar el programador limpio)
echo.
echo    2. Verifique el estado con: scripts\ver_estado.bat
echo.
echo ════════════════════════════════════════════════════════════════
echo.
pause
