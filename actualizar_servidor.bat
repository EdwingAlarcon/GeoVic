@echo off
chcp 65001 >nul

echo.
echo ================================================
echo   ACTUALIZAR GEOVICTORIA
echo   Para servidores con el proyecto ya instalado
echo ================================================
echo.
echo Este script:
echo   1. Detiene el programador en ejecucion
echo   2. Reemplaza SOLO el codigo fuente
echo   3. Instala dependencias nuevas si las hay
echo   4. Reinicia el programador
echo.
echo Conserva intactos: .env, config\employees.json, src\logs\, .venv
echo.
pause

cd /d "%~dp0"

REM --- Detectar Python del venv ---
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo [OK] Entorno virtual encontrado (.venv)
) else (
    set PYTHON=python
    echo [WARN] Usando Python del sistema
)
echo.

echo [1/4] Deteniendo programador...
taskkill /F /FI "WINDOWTITLE eq Programador GeoVictoria*" >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
if exist "src\logs\programador.lock" (
    del /F /Q "src\logs\programador.lock"
    echo       Lock file eliminado
)
echo [OK] Programador detenido
echo.

echo [2/4] Actualizando codigo fuente...
echo    Actualizando src\ (sin tocar src\logs\)...
xcopy /E /I /Y /Q src src /EXCLUDE:exportar_exclude.txt 2>nul
echo    Actualizando scripts\...
xcopy /E /I /Y /Q scripts scripts 2>nul
echo    Actualizando tests\...
if exist tests xcopy /E /I /Y /Q tests tests 2>nul
echo    Actualizando config\ (sin sobreescribir employees.json)...
if exist "config\selectors.json"         copy /Y "config\selectors.json"         "config\selectors.json" >nul
if exist "config\employees.example.json" copy /Y "config\employees.example.json" "config\employees.example.json" >nul
if exist requirements.txt copy /Y requirements.txt requirements.txt >nul
echo [OK] Codigo actualizado
echo.

echo [3/4] Instalando dependencias...
%PYTHON% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARN] Algunos paquetes no se pudieron instalar
    echo        Instala manualmente: %PYTHON% -m pip install -r requirements.txt
) else (
    echo [OK] Dependencias actualizadas
)
echo.

echo [4/4] Reiniciando programador...
start "Programador GeoVictoria" cmd /k "%PYTHON% src\programador.py"

echo.
echo ================================================
echo   ACTUALIZACION COMPLETADA
echo ================================================
echo.
echo [OK] Codigo actualizado
echo [OK] Dependencias instaladas
echo [OK] Programador reiniciado en nueva ventana
echo.
echo Para verificar: scripts\ver_estado.bat
echo.
pause
