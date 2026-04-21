@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
color 0A

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║          🚀 INSTALADOR DE GEOVICTORIA                          ║
echo ║          Sistema de Marcaje Automático                        ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

:: Verificar Python
echo [1/7] 🔍 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo.
    echo ❌ ERROR: Python no está instalado o no está en el PATH
    echo.
    echo 📥 Por favor instale Python desde: https://www.python.org/downloads/
    echo ⚠️  Durante la instalación, marque la opción "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
python --version
echo    ✅ Python encontrado
echo.

:: Verificar pip
echo [2/7] 🔍 Verificando pip...
pip --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ❌ ERROR: pip no está instalado
    pause
    exit /b 1
)
echo    ✅ pip encontrado
echo.

:: Crear entorno virtual
echo [3/7] 📦 Creando entorno virtual...
if exist .venv (
    echo    ⚠️  El entorno virtual ya existe, se usará el existente
) else (
    python -m venv .venv
    if errorlevel 1 (
        color 0C
        echo ❌ ERROR: No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
    echo    ✅ Entorno virtual creado
)
echo.

:: Activar entorno virtual
echo [4/7] 🔌 Activando entorno virtual...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    color 0C
    echo ❌ ERROR: No se pudo activar el entorno virtual
    pause
    exit /b 1
)
echo    ✅ Entorno virtual activado
echo.

:: Actualizar pip
echo [5/7] ⬆️  Actualizando pip...
python -m pip install --upgrade pip --quiet
echo    ✅ pip actualizado
echo.

:: Instalar dependencias
echo [6/7] 📚 Instalando dependencias de Python...
pip install -r requirements.txt
if errorlevel 1 (
    color 0C
    echo ❌ ERROR: Falló la instalación de dependencias
    pause
    exit /b 1
)
echo    ✅ Dependencias instaladas
echo.

:: Instalar Playwright
echo [7/7] 🌐 Instalando navegador Chromium para Playwright...
echo    ⏳ Esto puede tomar unos minutos...
playwright install chromium
if errorlevel 1 (
    color 0C
    echo ❌ ERROR: Falló la instalación de Playwright
    pause
    exit /b 1
)
echo    ✅ Playwright instalado correctamente
echo.

:: Configurar credenciales
echo ════════════════════════════════════════════════════════════════
echo.
if exist .env (
    echo 📝 El archivo .env ya existe
    echo.
    choice /C SN /M "¿Desea reemplazarlo con uno nuevo"
    if errorlevel 2 (
        echo    ⏭️  Se mantendrá el archivo .env existente
    ) else (
        copy /Y .env.example .env >nul
        echo    ✅ Archivo .env reemplazado
    )
) else (
    copy .env.example .env >nul
    echo ✅ Archivo .env creado desde .env.example
)
echo.

echo ════════════════════════════════════════════════════════════════
echo.
color 0B
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║          ✅ ¡INSTALACIÓN COMPLETADA CON ÉXITO!                 ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📋 PRÓXIMOS PASOS:
echo.
echo    1️⃣  Edite el archivo .env con sus credenciales de GeoVictoria
echo       - Abra el archivo .env con un editor de texto
echo       - Reemplace "su_usuario_aqui" con su usuario
echo       - Reemplace "su_contraseña_aqui" con su contraseña
echo       - Guarde el archivo
echo.
echo    2️⃣  Active el entorno virtual (en cada nueva terminal):
echo       .venv\Scripts\activate
echo.
echo    3️⃣  Ejecute el programa:
echo       - Prueba manual:        scripts\ejecutar_manual.bat
echo       - Programador auto:     scripts\iniciar_programador.bat
echo       - Ver estado:           scripts\ver_estado.bat
echo.
echo ════════════════════════════════════════════════════════════════
echo.
echo 📖 Para más información, consulte README.md
echo.
pause
