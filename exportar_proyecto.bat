@echo off
chcp 65001 >nul

echo.
echo ================================================
echo   EXPORTADOR DE GEOVICTORIA
echo   Preparar proyecto para distribucion
echo ================================================
echo.

cd /d "%~dp0"

set "EXPORT_NAME=GeoVic-Portable"
set "EXPORT_DIR=%TEMP%\%EXPORT_NAME%"
set "ZIP_FILE=%~dp0%EXPORT_NAME%.zip"

echo [1/5] Limpiando carpeta temporal...
if exist "%EXPORT_DIR%" rd /s /q "%EXPORT_DIR%"
mkdir "%EXPORT_DIR%"
echo    OK Carpeta temporal creada
echo.

echo [2/5] Copiando archivos del proyecto...
echo    Copiando codigo fuente (src/)...
xcopy /E /I /Q /Y src "%EXPORT_DIR%\src" /EXCLUDE:exportar_exclude.txt >nul 2>&1
echo    Copiando tests/...
if exist tests xcopy /E /I /Q /Y tests "%EXPORT_DIR%\tests" /EXCLUDE:exportar_exclude.txt >nul 2>&1
echo    Copiando scripts/...
xcopy /E /I /Q /Y scripts "%EXPORT_DIR%\scripts" >nul 2>&1
echo    Copiando docs/...
xcopy /E /I /Q /Y docs "%EXPORT_DIR%\docs" >nul 2>&1
echo    Copiando config/...
xcopy /E /I /Q /Y config "%EXPORT_DIR%\config" >nul 2>&1
echo    Copiando ajustes Claude Code...
if exist ".claude\settings.json" (
    mkdir "%EXPORT_DIR%\.claude" 2>nul
    copy /Y ".claude\settings.json" "%EXPORT_DIR%\.claude\" >nul
)
echo    Copiando archivos raiz...
if exist requirements.txt       copy /Y requirements.txt       "%EXPORT_DIR%\" >nul
if exist .env.example           copy /Y .env.example           "%EXPORT_DIR%\" >nul
if exist .gitignore             copy /Y .gitignore             "%EXPORT_DIR%\" >nul
if exist setup.bat              copy /Y setup.bat              "%EXPORT_DIR%\" >nul
if exist setup.sh               copy /Y setup.sh               "%EXPORT_DIR%\" >nul
if exist README.md              copy /Y README.md              "%EXPORT_DIR%\" >nul
if exist LEEME_PRIMERO.txt      copy /Y LEEME_PRIMERO.txt      "%EXPORT_DIR%\" >nul
if exist exportar_exclude.txt   copy /Y exportar_exclude.txt   "%EXPORT_DIR%\" >nul
if exist actualizar_servidor.bat copy /Y actualizar_servidor.bat "%EXPORT_DIR%\" >nul
if exist LICENSE                copy /Y LICENSE                "%EXPORT_DIR%\" >nul
echo    OK Archivos copiados
echo.

echo [3/5] Verificando archivos sensibles...
if exist "config\employees.json" (
    echo.
    echo    AVISO: Se encontro config\employees.json con credenciales.
    echo    Incluirlo solo si el destino es tu propio servidor.
    echo.
    choice /C SN /M "    Incluir employees.json en el ZIP? (S=Si / N=No)"
    if errorlevel 2 (
        if exist "%EXPORT_DIR%\config\employees.json" del /q "%EXPORT_DIR%\config\employees.json"
        echo    NO incluido - employees.json excluido del ZIP
    ) else (
        echo    SI incluido - recuerda que contiene contrasenas
    )
) else (
    echo    Sin config\employees.json - el servidor usara .env
)
echo.

echo [4/5] Limpiando archivos innecesarios...
powershell -NoProfile -Command "$d='%EXPORT_DIR%'; Remove-Item ($d+'\.env') -Force -EA 0; Remove-Item ($d+'\src\logs') -Recurse -Force -EA 0; Get-ChildItem $d -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force -EA 0; Get-ChildItem $d -Recurse -Directory -Filter '.pytest_cache' | Remove-Item -Recurse -Force -EA 0; Get-ChildItem $d -Recurse -Include '*.pyc','*.pyo','*.log','*.tmp','*.bak' | Remove-Item -Force -EA 0" >nul 2>&1
echo    OK Limpieza completada
echo.

echo [5/5] Creando archivo ZIP...
if exist "%ZIP_FILE%" del /q "%ZIP_FILE%"
powershell -Command "Compress-Archive -Path '%EXPORT_DIR%\*' -DestinationPath '%ZIP_FILE%' -CompressionLevel Optimal -ErrorAction SilentlyContinue"

if exist "%ZIP_FILE%" (
    echo    OK ZIP creado exitosamente
) else (
    echo    ERROR al crear el ZIP
    pause
    exit /b 1
)

rd /s /q "%EXPORT_DIR%"

echo.
echo ================================================
echo   EXPORTACION COMPLETADA
echo ================================================
echo.
echo Archivo: %EXPORT_NAME%.zip
for %%A in ("%ZIP_FILE%") do echo Tamano:  %%~zA bytes
echo.
echo ESCENARIO A - Servidor nuevo (primera instalacion):
echo   1. Copiar ZIP al servidor
echo   2. Extraer el ZIP
echo   3. Ejecutar setup.bat
echo   4. Configurar .env con credenciales
echo   5. Ejecutar scripts\iniciar_programador.bat
echo.
echo ESCENARIO B - Servidor existente (actualizar codigo):
echo   1. Copiar ZIP al servidor
echo   2. Extraer el ZIP en una carpeta temporal
echo   3. Ejecutar actualizar_servidor.bat
echo.
echo ================================================
echo.

explorer /select,"%ZIP_FILE%"
pause
