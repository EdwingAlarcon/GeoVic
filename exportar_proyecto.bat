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

echo [1/4] 🧹 Limpiando carpeta temporal...
if exist "%EXPORT_DIR%" rd /s /q "%EXPORT_DIR%"
mkdir "%EXPORT_DIR%"
echo    ✅ Carpeta temporal creada
echo.

echo [2/4] 📁 Copiando archivos del proyecto...
echo    Copiando código fuente...
xcopy /E /I /Q src "%EXPORT_DIR%\src" /EXCLUDE:exportar_exclude.txt 2>nul
echo    Copiando scripts...
xcopy /E /I /Q scripts "%EXPORT_DIR%\scripts" 2>nul
echo    Copiando documentación...
xcopy /E /I /Q docs "%EXPORT_DIR%\docs" 2>nul
echo    Copiando configuración...
xcopy /E /I /Q config "%EXPORT_DIR%\config" 2>nul

echo    Copiando archivos raíz...
copy /Y requirements.txt "%EXPORT_DIR%\" >nul
copy /Y .env.example "%EXPORT_DIR%\" >nul
copy /Y .gitignore "%EXPORT_DIR%\" >nul
copy /Y setup.bat "%EXPORT_DIR%\" >nul
copy /Y setup.sh "%EXPORT_DIR%\" >nul
copy /Y README.md "%EXPORT_DIR%\" >nul
copy /Y GUIA_INSTALACION.md "%EXPORT_DIR%\" >nul
copy /Y COMO_EXPORTAR.md "%EXPORT_DIR%\" >nul
copy /Y LEEME_PRIMERO.txt "%EXPORT_DIR%\" >nul
if exist LICENSE copy /Y LICENSE "%EXPORT_DIR%\" >nul

echo    ✅ Archivos copiados
echo.

echo [3/4] 🧹 Limpiando archivos sensibles e innecesarios...
:: Eliminar archivos sensibles
if exist "%EXPORT_DIR%\.env" del /q "%EXPORT_DIR%\.env"
if exist "%EXPORT_DIR%\src\logs" rd /s /q "%EXPORT_DIR%\src\logs"

:: Eliminar archivos de Python compilados
for /r "%EXPORT_DIR%" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q "%EXPORT_DIR%\*.pyc" 2>nul
del /s /q "%EXPORT_DIR%\*.pyo" 2>nul

:: Eliminar archivos temporales
del /s /q "%EXPORT_DIR%\*.log" 2>nul
del /s /q "%EXPORT_DIR%\*.tmp" 2>nul
del /s /q "%EXPORT_DIR%\*.bak" 2>nul

echo    ✅ Limpieza completada
echo.

echo [4/4] 📦 Creando archivo ZIP...
if exist "%ZIP_FILE%" del /q "%ZIP_FILE%"

:: Usar PowerShell para crear el ZIP
powershell -Command "Compress-Archive -Path '%EXPORT_DIR%\*' -DestinationPath '%ZIP_FILE%' -CompressionLevel Optimal"

if exist "%ZIP_FILE%" (
    echo    ✅ Archivo ZIP creado: %EXPORT_NAME%.zip
) else (
    color 0C
    echo    ❌ Error al crear el ZIP
    pause
    exit /b 1
)
echo.

echo [5/5] 🧹 Limpiando temporales...
rd /s /q "%EXPORT_DIR%"
echo    ✅ Temporales eliminados
echo.

echo ════════════════════════════════════════════════════════════════
echo.
color 0A
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║          ✅ ¡EXPORTACIÓN COMPLETADA!                           ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📦 Archivo creado: %EXPORT_NAME%.zip
echo.
for %%A in ("%ZIP_FILE%") do echo 📊 Tamaño: %%~zA bytes
echo.
echo 📋 CONTENIDO DEL ZIP:
echo    ✅ Código fuente completo
echo    ✅ Scripts de instalación y utilidad
echo    ✅ Documentación completa
echo    ✅ Archivo .env.example (plantilla)
echo    ✅ Archivo .gitignore (protección)
echo.
echo ❌ NO INCLUYE (protegido):
echo    ⛔ Archivo .env con credenciales
echo    ⛔ Entorno virtual (.venv)
echo    ⛔ Logs personales
echo    ⛔ Archivos compilados
echo.
echo ════════════════════════════════════════════════════════════════
echo.
echo 🎯 SIGUIENTE PASO:
echo    Comparta el archivo %EXPORT_NAME%.zip
echo.
echo 📖 INSTRUCCIONES PARA EL USUARIO FINAL:
echo    1. Extraer el ZIP
echo    2. Ejecutar setup.bat
echo    3. Configurar .env con sus credenciales
echo    4. Ejecutar scripts\ejecutar_manual.bat
echo.
echo ════════════════════════════════════════════════════════════════
echo.

:: Abrir explorador en la ubicación del ZIP
explorer /select,"%ZIP_FILE%"

pause
