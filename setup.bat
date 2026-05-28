@echo off
cd /d "%~dp0"
chcp 65001 >nul
setlocal
color 0A

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║          🚀 INSTALADOR DE GEOVICTORIA                          ║
echo ║          Sistema de Marcaje Automático                        ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

:: ============================================================================
:: PASO 0: VERIFICAR REQUISITOS PREVIOS
:: ============================================================================
echo [0/8] 🔍 Verificando requisitos del sistema...
echo.

:: Verificar Python instalado
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ❌ ERROR CRÍTICO: Python no está instalado o no está en el PATH
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo 💡 SOLUCIÓN:
    echo ════════════════════════════════════════════════════════════════
    echo.
    echo 1. Descargue Python 3.8 o superior desde:
    echo    https://www.python.org/downloads/
    echo.
    echo 2. Durante la instalación, ASEGÚRESE de marcar:
    echo    ☑ Add Python to PATH
    echo.
    echo 3. Reinicie esta terminal después de instalar
    echo.
    echo 4. Ejecute setup.bat nuevamente
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo.
    pause
    exit /b 1
)

:: Obtener y mostrar versión de Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    ✅ Python %PYTHON_VERSION% detectado
echo.

:: Verificar que la versión sea adecuada (3.8+)
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>nul
if errorlevel 1 (
    color 0E
    echo    ⚠️  ADVERTENCIA: Se recomienda Python 3.8 o superior
    echo     Tiene: %PYTHON_VERSION%
    echo     Continuando de todos modos...
    echo.
    timeout /t 3 /nobreak >nul
)

:: Verificar pip
echo [1/8] 🔍 Verificando pip (gestor de paquetes)...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo.
    echo ❌ ERROR: pip no está disponible
    echo.
    echo 💡 SOLUCIÓN:
    echo    Ejecute: python -m ensurepip --upgrade
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python -m pip --version 2^>^&1') do set PIP_VERSION=%%i
echo    ✅ pip %PIP_VERSION% encontrado
echo.

:: ============================================================================
:: PASO 2: CREAR ENTORNO VIRTUAL
:: ============================================================================
echo [2/8] 📦 Configurando entorno virtual Python...
echo.

if exist ".venv\Scripts\activate.bat" (
    echo     El entorno virtual ya existe en: .venv\
    echo     Se usará el entorno existente
    echo.
) else (
    echo    Creando entorno virtual ^(esto toma ~10 segundos^)...
    python -m venv .venv
    if errorlevel 1 (
        color 0C
        echo.
        echo    ❌ ERROR: No se pudo crear el entorno virtual
        echo.
        echo    💡 POSIBLES CAUSAS:
        echo       - Falta el módulo venv
        echo       - Permisos insuficientes
        echo       - Espacio en disco insuficiente
        echo.
        pause
        exit /b 1
    )
    echo    ✅ Entorno virtual creado correctamente
    echo.
)

:: ============================================================================
:: PASO 3: ACTIVAR ENTORNO VIRTUAL
:: ============================================================================
echo [3/8] 🔌 Activando entorno virtual...
echo.

if not exist ".venv\Scripts\activate.bat" (
    color 0C
    echo    ❌ ERROR: No se encontró el script de activación
    echo     Ruta esperada: .venv\Scripts\activate.bat
    echo.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    color 0C
    echo    ❌ ERROR: No se pudo activar el entorno virtual
    pause
    exit /b 1
)
echo    ✅ Entorno virtual activado
echo     Ruta: %VIRTUAL_ENV%
echo.

:: ============================================================================
:: PASO 4: ACTUALIZAR PIP
:: ============================================================================
echo [4/8] ⬆️  Actualizando pip a la última versión...
echo.

python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo    ⚠️  No se pudo actualizar pip, usando versión actual
) else (
    echo    ✅ pip actualizado correctamente
)
echo.

:: ============================================================================
:: PASO 5: INSTALAR DEPENDENCIAS DE PYTHON
:: ============================================================================
echo [5/8] 📚 Instalando dependencias de Python...
echo     Leyendo requirements.txt
echo.

if not exist "requirements.txt" (
    color 0C
    echo    ❌ ERROR: No se encontró el archivo requirements.txt
    echo.
    pause
    exit /b 1
)

echo    📦 Instalando: playwright, python-dotenv, apscheduler, psutil
echo    ⏳ Esto puede tomar 30-60 segundos dependiendo de su conexión...
echo.

python -m pip install -r requirements.txt
if errorlevel 1 (
    color 0C
    echo.
    echo    ❌ ERROR CRÍTICO: Falló la instalación de dependencias
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo 💡 POSIBLES CAUSAS Y SOLUCIONES:
    echo ════════════════════════════════════════════════════════════════
    echo.
    echo 1. Sin conexión a Internet
    echo    → Verifique su conexión
    echo.
    echo 2. Firewall o proxy bloqueando pip
    echo    → Configure proxy: set HTTP_PROXY=http://proxy:puerto
    echo.
    echo 3. Archivo requirements.txt dañado
    echo    → Re-descargue el proyecto
    echo.
    echo 4. Permisos insuficientes
    echo    → Ejecute como Administrador
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo.
    pause
    exit /b 1
)
echo    ✅ Todas las dependencias instaladas correctamente
echo.

:: Verificar que playwright se instaló
python -c "import playwright; print('✅ playwright:', playwright.__version__)" 2>nul
if errorlevel 1 (
    echo    ⚠️  ADVERTENCIA: playwright no se importó correctamente
)

:: Verificar que dotenv se instaló
python -c "import dotenv; print('✅ python-dotenv instalado')" 2>nul
if errorlevel 1 (
    echo    ⚠️  ADVERTENCIA: python-dotenv no se importó correctamente
)

:: Verificar apscheduler
python -c "import apscheduler; print('✅ apscheduler instalado')" 2>nul
if errorlevel 1 (
    echo    ⚠️  ADVERTENCIA: apscheduler no se importó correctamente
)

echo.

:: ============================================================================
:: PASO 6: INSTALAR NAVEGADORES DE PLAYWRIGHT
:: ============================================================================
echo [6/8] 🌐 Instalando navegador Chromium para Playwright...
echo     Se descargarán aproximadamente 170 MB
echo    ⏳ Esto puede tomar 2-5 minutos dependiendo de su conexión...
echo.

python -m playwright install chromium
if errorlevel 1 (
    color 0C
    echo.
    echo    ❌ ERROR: Falló la instalación del navegador Chromium
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo 💡 SOLUCIONES:
    echo ════════════════════════════════════════════════════════════════
    echo.
    echo 1. Verifique su conexión a Internet
    echo.
    echo 2. Intente instalar manualmente:
    echo    .venv\Scripts\activate
    echo    playwright install chromium --force
    echo.
    echo 3. Si el problema persiste, reinstale playwright:
    echo    pip uninstall playwright -y
    echo    pip install playwright
    echo    playwright install chromium
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo.
    pause
    exit /b 1
)
echo    ✅ Navegador Chromium instalado correctamente
echo.

:: ============================================================================
:: PASO 7: CONFIGURAR ARCHIVO DE CREDENCIALES
:: ============================================================================
echo [7/8] 🔐 Configurando archivo de variables de entorno...
echo.

if exist ".env" (
    echo     El archivo .env ya existe
    echo.
    choice /C SN /M "¿Desea reemplazarlo con la plantilla"
    if errorlevel 2 (
        echo    ⏭️  Se mantendrá el archivo .env existente
        echo.
    ) else (
        if exist ".env.example" (
            copy /Y .env.example .env >nul
            echo    ✅ Archivo .env reemplazado desde .env.example
        ) else (
            echo    ⚠️  .env.example no encontrado, creando .env básico
            (
                echo # Configuración GeoVictoria
                echo # IMPORTANTE: Reemplace con sus credenciales reales
                echo.
                echo GEOVICTORIA_USER=su_usuario_aqui
                echo GEOVICTORIA_PASSWORD=su_contraseña_aqui
            ) > .env
            echo    ✅ Archivo .env básico creado
        )
        echo.
    )
) else (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo    ✅ Archivo .env creado desde .env.example
    ) else (
        echo    ⚠️  .env.example no encontrado, creando .env básico
        (
            echo # Configuración GeoVictoria
            echo # IMPORTANTE: Reemplace con sus credenciales reales
            echo.
            echo GEOVICTORIA_USER=su_usuario_aqui
            echo GEOVICTORIA_PASSWORD=su_contraseña_aqui
        ) > .env
        echo    ✅ Archivo .env básico creado
    )
    echo.
)

:: ============================================================================
:: PASO 8: VERIFICACIÓN FINAL
:: ============================================================================
echo [8/8] ✔️  Verificando instalación completa...
echo.

set ERROR_COUNT=0

:: Verificar entorno virtual
if exist ".venv\Scripts\python.exe" (
    echo    ✅ Entorno virtual: OK
) else (
    echo    ❌ Entorno virtual: ERROR
    set /a ERROR_COUNT+=1
)

:: Verificar dependencias críticas
python -c "import playwright, dotenv, apscheduler, psutil" 2>nul
if errorlevel 1 (
    echo    ❌ Dependencias: INCOMPLETAS
    set /a ERROR_COUNT+=1
) else (
    echo    ✅ Dependencias: OK
)

:: Verificar archivo .env
if exist ".env" (
    echo    ✅ Archivo .env: OK
) else (
    echo    ❌ Archivo .env: NO EXISTE
    set /a ERROR_COUNT+=1
)

:: Verificar archivos principales
if exist "src\geovictoria.py" (
    echo    ✅ Código fuente: OK
) else (
    echo    ❌ Código fuente: FALTA src\geovictoria.py
    set /a ERROR_COUNT+=1
)

echo.

if %ERROR_COUNT% GTR 0 (
    color 0E
    echo    Se encontraron %ERROR_COUNT% problema^(s^)
    echo     El sistema puede no funcionar correctamente
    echo.
) else (
    echo    ✅ Todas las verificaciones pasaron correctamente
    echo.
)

:: ============================================================================
:: INSTALACIÓN COMPLETADA
:: ============================================================================
echo ════════════════════════════════════════════════════════════════
echo.
color 0B
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║          ✅ ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!              ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo ════════════════════════════════════════════════════════════════
echo 📋 PRÓXIMOS PASOS (IMPORTANTE):
echo ════════════════════════════════════════════════════════════════
echo.
echo PASO 1: Configurar sus credenciales (OBLIGATORIO)
echo ────────────────────────────────────────────────────────────────
echo.
echo    Edite el archivo .env con sus credenciales de GeoVictoria:
echo.
echo    📝 Opción A: Editar con Bloc de notas
echo       notepad .env
echo.
echo    📝 Opción B: Editar con Visual Studio Code
echo       code .env
echo.
echo    Reemplace estas líneas:
echo       GEOVICTORIA_USER=su_usuario_aqui
echo       GEOVICTORIA_PASSWORD=su_contraseña_aqui
echo.
echo    Con sus datos reales, por ejemplo:
echo       GEOVICTORIA_USER=juan.perez
echo       GEOVICTORIA_PASSWORD=MiContraseña123
echo.
echo    ⚠️  Guarde el archivo después de editar
echo.
echo ════════════════════════════════════════════════════════════════
echo.
echo PASO 2: Verificar que todo está correcto
echo ────────────────────────────────────────────────────────────────
echo.
echo    scripts\verificar_instalacion.bat
echo.
echo ════════════════════════════════════════════════════════════════
echo.
echo PASO 3: Probar el sistema
echo ────────────────────────────────────────────────────────────────
echo.
echo    🧪 Marcaje manual (una vez):
echo       scripts\ejecutar_manual.bat
echo.
echo    ⚙️  Programador automático (recomendado):
echo       scripts\iniciar_programador.bat
echo.
echo    📊 Ver estado del sistema:
echo       scripts\ver_estado.bat
echo.
echo ════════════════════════════════════════════════════════════════
echo.
echo 💡 CONSEJOS ÚTILES:
echo ════════════════════════════════════════════════════════════════
echo.
echo    • El entorno virtual se activa automáticamente en los scripts
echo    • Para activarlo manualmente: .venv\Scripts\activate
echo    • Para desactivarlo: deactivate
echo    • Documentación completa: docs\GUIA_INSTALACION.md
echo    • Ver festivos de Colombia: scripts\ver_festivos.bat
echo.
echo ════════════════════════════════════════════════════════════════
echo.
echo 📖 DOCUMENTACIÓN ADICIONAL:
echo.
echo    • README.md                - Información general
echo    • docs\GUIA_INSTALACION.md - Guía completa paso a paso
echo    • docs\COMO_EXPORTAR.md    - Compartir con otros usuarios
echo    • LEEME_PRIMERO.txt        - Inicio rápido
echo.
echo ════════════════════════════════════════════════════════════════
echo.
echo 🔒 IMPORTANTE - SEGURIDAD:
echo.
echo    ⚠️  NO comparta el archivo .env con nadie
echo    ⚠️  NO suba el archivo .env a GitHub o Internet
echo    ✅  El archivo .gitignore ya lo protege automáticamente
echo.
echo ════════════════════════════════════════════════════════════════
echo.

pause
endlocal
