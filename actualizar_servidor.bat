@echo off
chcp 65001 >nul
color 0B

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║          🔄 ACTUALIZAR GEOVICTORIA                             ║
echo ║          Para servidores con el proyecto ya instalado         ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo Este script:
echo   1. Detiene el programador en ejecución
echo   2. Reemplaza SOLO el código (src/, scripts/, config/, tests/)
echo   3. Instala dependencias nuevas si las hay
echo   4. Reinicia el programador
echo.
echo ✅ Conserva intactos: .env, config\employees.json, src\logs\, .venv
echo.
pause

REM Detectar raíz del proyecto (donde está este .bat)
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

REM ============================================
REM 1. DETENER PROGRAMADOR
REM ============================================
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

REM ============================================
REM 2. RESPALDAR Y REEMPLAZAR CÓDIGO
REM ============================================
echo [2/4] Actualizando código fuente...

REM src\ — reemplazar solo archivos .py, NO tocar src\logs\
echo    Actualizando src\...
for %%f in (src\*.py) do (
    copy /Y "%%f" "%%f" >nul 2>&1
)
REM xcopy reemplaza archivos existentes, crea nuevos, respeta /EXCLUDE
xcopy /E /I /Y /Q src "%~dp0src" /EXCLUDE:exportar_exclude.txt 2>nul

echo    Actualizando scripts\...
xcopy /E /I /Y /Q scripts "%~dp0scripts" 2>nul

echo    Actualizando tests\...
if exist tests (
    xcopy /E /I /Y /Q tests "%~dp0tests" 2>nul
)

echo    Actualizando config\ ^(sin sobreescribir employees.json^)...
if exist "config\selectors.json" copy /Y "config\selectors.json" "%~dp0config\selectors.json" >nul
if exist "config\employees.example.json" copy /Y "config\employees.example.json" "%~dp0config\employees.example.json" >nul

echo    Actualizando requirements.txt...
if exist requirements.txt copy /Y requirements.txt "%~dp0requirements.txt" >nul

echo [OK] Código actualizado
echo.

REM ============================================
REM 3. INSTALAR DEPENDENCIAS NUEVAS
REM ============================================
echo [3/4] Verificando dependencias...
%PYTHON% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARN] Algunos paquetes no se pudieron instalar
    echo        Verifica la conexión o instala manualmente:
    echo        %PYTHON% -m pip install -r requirements.txt
) else (
    echo [OK] Dependencias actualizadas
)
echo.

REM ============================================
REM 4. REINICIAR PROGRAMADOR
REM ============================================
echo [4/4] Reiniciando programador...
echo.
echo Se abrirá una nueva ventana con el programador.
echo NO cierre esa ventana — es el proceso principal.
echo.
timeout /t 2 /nobreak >nul

start "Programador GeoVictoria" cmd /k "%PYTHON% src\programador.py"

echo.
color 0A
echo ╔════════════════════════════════════════════════════════════════╗
echo ║          ✅ ACTUALIZACIÓN COMPLETADA                           ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo ✅ Código actualizado
echo ✅ Dependencias instaladas
echo ✅ Programador reiniciado en nueva ventana
echo.
echo Para verificar que funciona:
echo    scripts\ver_estado.bat
echo.
pause
