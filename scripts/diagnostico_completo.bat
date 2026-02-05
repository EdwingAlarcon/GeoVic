@echo off
setlocal enabledelayedexpansion

echo ================================================================================
echo   DIAGNOSTICO COMPLETO GEOVICTORIA
echo   Fecha: %date% %time%
echo ================================================================================
echo.

REM ============================================================================
REM 1. VERIFICAR PROCESOS
REM ============================================================================
echo [1/6] Verificando procesos en ejecucion...
echo ----------------------------------------

set PROCESO_ENCONTRADO=0
for /f "tokens=*" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2^>NUL') do (
    set PROCESO_ENCONTRADO=1
    echo     [ENCONTRADO] %%i
)

if !PROCESO_ENCONTRADO!==0 (
    echo     [ADVERTENCIA] No hay procesos python.exe corriendo
    echo     [SOLUCION] El programador NO esta activo
) else (
    echo     [OK] Python esta corriendo
)
echo.

REM ============================================================================
REM 2. VERIFICAR ARCHIVOS CRITICOS
REM ============================================================================
echo [2/6] Verificando archivos criticos...
echo ----------------------------------------

if exist ".env" (
    echo     [OK] Archivo .env encontrado
) else (
    echo     [ERROR] Archivo .env NO encontrado
    echo     [SOLUCION] Crear archivo .env con credenciales
)

if exist "src\programador.py" (
    echo     [OK] programador.py encontrado
) else (
    echo     [ERROR] programador.py NO encontrado
)

if exist "src\geovictoria.py" (
    echo     [OK] geovictoria.py encontrado
) else (
    echo     [ERROR] geovictoria.py NO encontrado
)
echo.

REM ============================================================================
REM 3. VERIFICAR LOGS
REM ============================================================================
echo [3/6] Verificando logs del dia...
echo ----------------------------------------

for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
set LOG_FILE=src\logs\programador_%mydate%.log

if exist "%LOG_FILE%" (
    echo     [OK] Log de hoy encontrado: %LOG_FILE%
    for %%A in ("%LOG_FILE%") do set LOG_SIZE=%%~zA
    if !LOG_SIZE! GTR 0 (
        echo     [OK] Tamano del log: !LOG_SIZE! bytes
        echo.
        echo     Ultimas 20 lineas del log:
        echo     ----------------------------------------
        powershell -Command "Get-Content '%LOG_FILE%' -Tail 20 -ErrorAction SilentlyContinue"
    ) else (
        echo     [ADVERTENCIA] El archivo de log esta vacio
        echo     [POSIBLE CAUSA] El programador no se ha iniciado hoy o hay problemas de permisos
    )
) else (
    echo     [ADVERTENCIA] No existe log para hoy: %LOG_FILE%
    echo     [POSIBLE CAUSA] El programador no se ha iniciado hoy
)
echo.

REM ============================================================================
REM 4. VERIFICAR REGISTRO DE EJECUCIONES
REM ============================================================================
echo [4/6] Verificando registro de ejecuciones...
echo ----------------------------------------

if exist "src\logs\registro_ejecuciones.json" (
    echo     [OK] Archivo de registro encontrado
    echo.
    echo     Ultimas ejecuciones:
    echo     ----------------------------------------
    python -c "import json; f=open('src/logs/registro_ejecuciones.json','r',encoding='utf-8'); data=json.load(f); f.close(); import sys; [print(f'     {fecha}: {list(marcajes.keys())}') for fecha, marcajes in sorted(data.items(), reverse=True)[:7]]" 2>NUL
    if errorlevel 1 (
        echo     [ERROR] No se pudo leer el archivo JSON
        echo     [SOLUCION] El archivo puede estar corrupto
    )
) else (
    echo     [ADVERTENCIA] No existe registro de ejecuciones
    echo     [INFO] Se creara cuando se ejecute el primer marcaje
)
echo.

REM ============================================================================
REM 5. VERIFICAR ESTADO EN GEOVICTORIA
REM ============================================================================
echo [5/6] Verificando estado actual en GeoVictoria...
echo ----------------------------------------
python scripts\verificar_estado.py
echo.

REM ============================================================================
REM 6. VERIFICAR DEPENDENCIAS
REM ============================================================================
echo [6/6] Verificando dependencias de Python...
echo ----------------------------------------

python -c "import playwright" 2>NUL
if errorlevel 1 (
    echo     [ERROR] playwright NO instalado
    echo     [SOLUCION] pip install playwright ^&^& playwright install chromium
) else (
    echo     [OK] playwright instalado
)

python -c "import dotenv" 2>NUL
if errorlevel 1 (
    echo     [ERROR] python-dotenv NO instalado
    echo     [SOLUCION] pip install python-dotenv
) else (
    echo     [OK] python-dotenv instalado
)

python -c "import apscheduler" 2>NUL
if errorlevel 1 (
    echo     [ERROR] apscheduler NO instalado
    echo     [SOLUCION] pip install apscheduler
) else (
    echo     [OK] apscheduler instalado
)
echo.

REM ============================================================================
REM RESUMEN Y RECOMENDACIONES
REM ============================================================================
echo ================================================================================
echo   RESUMEN Y RECOMENDACIONES
echo ================================================================================

if !PROCESO_ENCONTRADO!==0 (
    echo.
    echo [ACCION REQUERIDA] El programador NO esta corriendo
    echo.
    echo Para iniciarlo:
    echo   1. Ejecutar: scripts\iniciar_programador.bat
    echo   2. O configurar Tarea Programada de Windows (ver CONFIGURAR_TAREA_WINDOWS.md^)
    echo.
)

echo Para mas informacion sobre configuracion:
echo   - Ver: CONFIGURAR_TAREA_WINDOWS.md
echo   - Logs en: src\logs\
echo   - Verificar estado: scripts\ver_estado_detallado.bat
echo.
echo ================================================================================

pause
