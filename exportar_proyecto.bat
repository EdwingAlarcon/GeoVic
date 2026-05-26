@echo off
chcp 65001 >nul
color 0B

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║          📦 EXPORTADOR DE GEOVICTORIA                          ║
echo ║          Preparar proyecto para distribución                  ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

set "EXPORT_NAME=GeoVic-Portable"
set "EXPORT_DIR=%TEMP%\%EXPORT_NAME%"
set "ZIP_FILE=%cd%\%EXPORT_NAME%.zip"

echo [1/5] 🧹 Limpiando carpeta temporal...
if exist "%EXPORT_DIR%" rd /s /q "%EXPORT_DIR%"
mkdir "%EXPORT_DIR%"
echo    ✅ Carpeta temporal creada
echo.

echo [2/5] 📁 Copiando archivos del proyecto...
echo    Copiando código fuente...
xcopy /E /I /Q src "%EXPORT_DIR%\src" /EXCLUDE:exportar_exclude.txt 2>nul
echo    Copiando tests...
xcopy /E /I /Q tests "%EXPORT_DIR%\tests" /EXCLUDE:exportar_exclude.txt 2>nul
echo    Copiando scripts...
xcopy /E /I /Q scripts "%EXPORT_DIR%\scripts" 2>nul
echo    Copiando documentación...
xcopy /E /I /Q docs "%EXPORT_DIR%\docs" 2>nul
echo    Copiando configuración...
xcopy /E /I /Q config "%EXPORT_DIR%\config" 2>nul
echo    Copiando ajustes Claude Code...
if exist ".claude\settings.json" (
    mkdir "%EXPORT_DIR%\.claude" 2>nul
    copy /Y ".claude\settings.json" "%EXPORT_DIR%\.claude\" >nul
)

echo    Copiando archivos raíz...
copy /Y requirements.txt "%EXPORT_DIR%\" >nul
copy /Y .env.example "%EXPORT_DIR%\" >nul
copy /Y .gitignore "%EXPORT_DIR%\" >nul
copy /Y setup.bat "%EXPORT_DIR%\" >nul
copy /Y setup.sh "%EXPORT_DIR%\" >nul
copy /Y README.md "%EXPORT_DIR%\" >nul
copy /Y LEEME_PRIMERO.txt "%EXPORT_DIR%\" >nul
if exist LICENSE copy /Y LICENSE "%EXPORT_DIR%\" >nul
echo    ✅ Archivos copiados
echo.

echo [3/5] 🔒 Verificando archivos sensibles...
REM employees.json tiene credenciales — preguntar al usuario
if exist "config\employees.json" (
    echo.
    echo    ⚠️  Se encontró config\employees.json con credenciales de empleados.
    echo    ¿Incluirlo en el ZIP? Solo si el destino es tu propio servidor.
    echo.
    choice /C SN /M "    Incluir employees.json (S=Si / N=No)"
    if errorlevel 2 (
        del /q "%EXPORT_DIR%\config\employees.json" 2>nul
        echo    ⛔ employees.json excluido del ZIP
    ) else (
        echo    ✅ employees.json incluido ^(recuerda que contiene contraseñas^)
    )
) else (
    echo    ℹ️  No hay config\employees.json — el servidor usará .env
)
echo.

echo [4/5] 🧹 Limpiando archivos innecesarios...
if exist "%EXPORT_DIR%\.env" del /q "%EXPORT_DIR%\.env"
if exist "%EXPORT_DIR%\src\logs" rd /s /q "%EXPORT_DIR%\src\logs"
for /r "%EXPORT_DIR%" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q "%EXPORT_DIR%\*.pyc" 2>nul
del /s /q "%EXPORT_DIR%\*.pyo" 2>nul
del /s /q "%EXPORT_DIR%\*.log" 2>nul
del /s /q "%EXPORT_DIR%\*.tmp" 2>nul
del /s /q "%EXPORT_DIR%\*.bak" 2>nul
echo    ✅ Limpieza completada
echo.

echo [5/5] 📦 Creando archivo ZIP...
if exist "%ZIP_FILE%" del /q "%ZIP_FILE%"
powershell -Command "Compress-Archive -Path '%EXPORT_DIR%\*' -DestinationPath '%ZIP_FILE%' -CompressionLevel Optimal"

if exist "%ZIP_FILE%" (
    echo    ✅ Archivo ZIP creado: %EXPORT_NAME%.zip
) else (
    color 0C
    echo    ❌ Error al crear el ZIP
    pause
    exit /b 1
)

rd /s /q "%EXPORT_DIR%"
echo.

echo ════════════════════════════════════════════════════════════════
color 0A
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║          ✅ ¡EXPORTACIÓN COMPLETADA!                           ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📦 Archivo: %EXPORT_NAME%.zip
for %%A in ("%ZIP_FILE%") do echo 📊 Tamaño:  %%~zA bytes
echo.
echo ════════════════════════════════════════════════════════════════
echo.
echo 🎯 DOS ESCENARIOS DE USO:
echo.
echo   A) INSTALACIÓN NUEVA en el servidor:
echo      1. Copiar ZIP al servidor
echo      2. Extraer el ZIP
echo      3. Ejecutar setup.bat
echo      4. Configurar .env con credenciales
echo      5. Ejecutar scripts\iniciar_programador.bat
echo.
echo   B) ACTUALIZAR servidor existente:
echo      1. Copiar ZIP al servidor
echo      2. Ejecutar actualizar_servidor.bat ^(incluido en el ZIP^)
echo      3. Reiniciar con scripts\reiniciar_programador.bat
echo.
echo ════════════════════════════════════════════════════════════════
echo.

explorer /select,"%ZIP_FILE%"
pause
