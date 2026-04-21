@echo off
chcp 65001 >nul
color 0B

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║          🔍 VERIFICACIÓN DE INSTALACIÓN                        ║
echo ║          GeoVictoria - Sistema de Marcaje                     ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

set ERROR_COUNT=0

:: Verificar Python
echo [1/7] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo    ❌ Python NO instalado
    set /a ERROR_COUNT+=1
) else (
    for /f "tokens=*" %%i in ('python --version') do echo    ✅ %%i
)
echo.

:: Verificar pip
echo [2/7] Verificando pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo    ❌ pip NO instalado
    set /a ERROR_COUNT+=1
) else (
    for /f "tokens=1-2" %%i in ('pip --version') do echo    ✅ %%i %%j
)
echo.

:: Verificar entorno virtual
echo [3/7] Verificando entorno virtual...
if exist .venv\ (
    echo    ✅ Entorno virtual existe (.venv)
) else (
    echo    ❌ Entorno virtual NO existe
    echo       Ejecute: python -m venv .venv
    set /a ERROR_COUNT+=1
)
echo.

:: Verificar dependencias
echo [4/7] Verificando dependencias de Python...
call .venv\Scripts\activate.bat 2>nul
pip show playwright >nul 2>&1
if errorlevel 1 (
    echo    ❌ Playwright NO instalado
    set /a ERROR_COUNT+=1
) else (
    echo    ✅ Playwright instalado
)

pip show python-dotenv >nul 2>&1
if errorlevel 1 (
    echo    ❌ python-dotenv NO instalado
    set /a ERROR_COUNT+=1
) else (
    echo    ✅ python-dotenv instalado
)

pip show apscheduler >nul 2>&1
if errorlevel 1 (
    echo    ❌ APScheduler NO instalado
    set /a ERROR_COUNT+=1
) else (
    echo    ✅ APScheduler instalado
)

pip show psutil >nul 2>&1
if errorlevel 1 (
    echo    ❌ psutil NO instalado
    set /a ERROR_COUNT+=1
) else (
    echo    ✅ psutil instalado
)
echo.

:: Verificar archivo .env
echo [5/7] Verificando configuración...
if exist .env (
    echo    ✅ Archivo .env existe
    
    findstr /C:"GEOVICTORIA_USER=su_usuario_aqui" .env >nul 2>&1
    if not errorlevel 1 (
        echo    ⚠️  ADVERTENCIA: Credenciales no configuradas en .env
        echo       Edite el archivo .env con sus credenciales reales
        set /a ERROR_COUNT+=1
    ) else (
        echo    ✅ Credenciales configuradas
    )
) else (
    echo    ❌ Archivo .env NO existe
    echo       Copie .env.example a .env y configure sus credenciales
    set /a ERROR_COUNT+=1
)
echo.

:: Verificar estructura de carpetas
echo [6/7] Verificando estructura del proyecto...
if exist src\ (
    echo    ✅ Carpeta src/
) else (
    echo    ❌ Carpeta src/ NO existe
    set /a ERROR_COUNT+=1
)

if exist scripts\ (
    echo    ✅ Carpeta scripts/
) else (
    echo    ❌ Carpeta scripts/ NO existe
    set /a ERROR_COUNT+=1
)

if exist requirements.txt (
    echo    ✅ Archivo requirements.txt
) else (
    echo    ❌ Archivo requirements.txt NO existe
    set /a ERROR_COUNT+=1
)
echo.

:: Verificar archivos principales
echo [7/7] Verificando archivos principales...
if exist src\geovictoria.py (
    echo    ✅ src\geovictoria.py
) else (
    echo    ❌ src\geovictoria.py NO existe
    set /a ERROR_COUNT+=1
)

if exist src\programador.py (
    echo    ✅ src\programador.py
) else (
    echo    ❌ src\programador.py NO existe
    set /a ERROR_COUNT+=1
)

if exist src\festivos_colombia.py (
    echo    ✅ src\festivos_colombia.py
) else (
    echo    ❌ src\festivos_colombia.py NO existe
    set /a ERROR_COUNT+=1
)
echo.

echo ════════════════════════════════════════════════════════════════
echo.

if %ERROR_COUNT% EQU 0 (
    color 0A
    echo ╔════════════════════════════════════════════════════════════════╗
    echo ║                                                                ║
    echo ║          ✅ ¡INSTALACIÓN CORRECTA!                             ║
    echo ║          Todos los componentes están instalados               ║
    echo ║                                                                ║
    echo ╚════════════════════════════════════════════════════════════════╝
    echo.
    echo 🚀 El sistema está listo para usarse:
    echo.
    echo    - Prueba manual:     scripts\ejecutar_manual.bat
    echo    - Programador auto:  scripts\iniciar_programador.bat
    echo    - Ver estado:        scripts\ver_estado.bat
    echo.
) else (
    color 0C
    echo ╔════════════════════════════════════════════════════════════════╗
    echo ║                                                                ║
    echo ║          ❌ SE ENCONTRARON %ERROR_COUNT% ERRORES                             ║
    echo ║          Por favor corrija los problemas indicados            ║
    echo ║                                                                ║
    echo ╚════════════════════════════════════════════════════════════════╝
    echo.
    echo 💡 SOLUCIONES:
    echo.
    echo    1. Si Python no está instalado:
    echo       - Descargue desde: https://www.python.org/downloads/
    echo       - Marque "Add Python to PATH" durante instalación
    echo.
    echo    2. Si faltan dependencias:
    echo       - Ejecute: setup.bat
    echo.
    echo    3. Si el archivo .env no existe:
    echo       - Ejecute: copy .env.example .env
    echo       - Edite .env con sus credenciales
    echo.
)

echo ════════════════════════════════════════════════════════════════
echo.
pause
