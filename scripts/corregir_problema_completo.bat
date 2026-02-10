@echo off
echo ========================================
echo   CORRECCION COMPLETA DEL PROBLEMA
echo   Marcajes Multiples Duplicados
echo ========================================
echo.
echo Este script hara lo siguiente:
echo   1. Detener TODAS las instancias de Python (requiere admin)
echo   2. Eliminar archivos de lock
echo   3. Limpiar registro de marcajes de HOY
echo   4. Iniciar UNA SOLA instancia del programador
echo.
pause

REM ============================================
REM 1. DETENER PROCESOS (requiere permisos admin)
REM ============================================
echo.
echo [1/4] Deteniendo procesos de Python...
echo.
echo IMPORTANTE: Si aparecen errores de "Acceso denegado":
echo   1. Cierre esta ventana
echo   2. Click derecho en este archivo
echo   3. Seleccione "Ejecutar como administrador"
echo.

taskkill /F /IM python.exe 2>nul
if errorlevel 1 (
    echo.
    echo [ADVERTENCIA] No se pudieron detener algunos procesos
    echo Esto puede significar:
    echo   - No hay procesos corriendo (OK)
    echo   - Necesita permisos de administrador
    echo.
    echo Continuando de todas formas...
) else (
    echo [OK] Procesos Python detenidos
)

timeout /t 3 >nul

REM ============================================
REM 2. ELIMINAR LOCK FILES
REM ============================================
echo.
echo [2/4] Eliminando archivos de lock...
cd /d "%~dp0\.."

if exist "src\logs\programador.lock" (
    del /F /Q "src\logs\programador.lock" 2>nul
    echo [OK] Lock file eliminado
) else (
    echo [INFO] No habia lock file
)

REM ============================================
REM 3. LIMPIAR REGISTRO DE HOY
REM ============================================
echo.
echo [3/4] Limpiando registro de marcajes de hoy...
python scripts\limpiar_registro_hoy.py
if errorlevel 1 (
    echo [ADVERTENCIA] Error limpiando registro
) else (
    echo [OK] Registro limpiado
)

REM ============================================
REM 4. VERIFICAR QUE NO QUEDEN PROCESOS
REM ============================================
echo.
echo [VERIFICACION] Comprobando que no quedan procesos...
tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2>nul | find /I "python.exe" >nul
if errorlevel 1 (
    echo [OK] No hay procesos Python corriendo
) else (
    echo.
    echo [ADVERTENCIA] Aun hay procesos Python corriendo:
    tasklist /FI "IMAGENAME eq python.exe" /FO TABLE
    echo.
    echo Desea continuar de todas formas? (S/N)
    choice /C SN /N
    if errorlevel 2 goto :fin
)

REM ============================================
REM 5. ESPERAR UN MOMENTO
REM ============================================
echo.
echo Esperando 5 segundos antes de reiniciar...
timeout /t 5 >nul

REM ============================================
REM 6. INICIAR PROGRAMADOR
REM ============================================
echo.
echo [4/4] Iniciando programador (UNA SOLA INSTANCIA)...
echo.
echo ========================================
echo   IMPORTANTE
echo ========================================
echo Se abrira una nueva ventana con el programador
echo NO CIERRE ESA VENTANA
echo Puede minimizarla pero NO cerrarla
echo ========================================
echo.
timeout /t 3 >nul

start "Programador GeoVictoria" cmd /k "cd /d "%~dp0\.." && python src\programador.py"

echo.
echo ========================================
echo   PROCESO COMPLETADO
echo ========================================
echo.
echo El programador esta corriendo en una ventana separada
echo.
echo Verifique que:
echo   [x] Solo hay UNA ventana del programador
echo   [x] Los horarios se muestran correctamente
echo   [x] No hay errores en pantalla
echo.
echo Puede cerrar ESTA ventana ahora
echo (NO cierre la ventana del programador)
echo ========================================
echo.

:fin
pause
