@echo off
chcp 65001 >nul
REM Actualiza una instalacion existente de GeoVic en el servidor.
REM
REM USO: extraer GeoVic-Portable.zip en una carpeta temporal y ejecutar ESTE archivo desde ahi.
REM Pide la ruta de la carpeta del proyecto instalado y copia el codigo nuevo encima.
REM
REM Conserva: .env, config\employees.json, config\festivos_adicionales.json, src\logs, .venv
REM Requiere Administrador (se solicita automaticamente).

set "TASK=GeoVictoria Programador"

echo.
echo ================================================
echo   ACTUALIZAR GEOVICTORIA (servidor)
echo ================================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de Administrador...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

REM --- Origen: carpeta donde esta este script (el zip extraido) ---
set "SRC=%~dp0"
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"

if not exist "%SRC%\src\programador.py" (
    echo [ERROR] No encuentro src\programador.py junto a este script.
    echo         Ejecutalo desde la carpeta donde extrajiste GeoVic-Portable.zip.
    echo.
    pause
    exit /b 1
)

REM --- Destino: carpeta del proyecto instalado ---
echo Origen (zip extraido): %SRC%
echo.
set "TARGET="
set /p "TARGET=Ruta de la carpeta del proyecto instalado (ej: C:\GeoVic): "
set "TARGET=%TARGET:"=%"
if not defined TARGET (
    echo [ERROR] No indicaste ninguna ruta.
    echo.
    pause
    exit /b 1
)
for %%I in ("%TARGET%") do set "TARGET=%%~fI"
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"

if /I "%SRC%"=="%TARGET%" (
    echo [ERROR] El origen y el destino son la misma carpeta.
    echo         Extrae el zip en una carpeta temporal y ejecuta el script desde ahi.
    echo.
    pause
    exit /b 1
)
if not exist "%TARGET%\src\programador.py" (
    echo [ERROR] "%TARGET%" no parece un proyecto GeoVic instalado ^(falta src\programador.py^).
    echo         Si es una instalacion nueva, usa setup.bat en lugar de este script.
    echo.
    pause
    exit /b 1
)

echo Destino: %TARGET%
echo.
echo Se detendra el programador, se copiara el codigo nuevo y se volvera a iniciar.
echo Se conservan: .env, config\employees.json, config\festivos_adicionales.json, src\logs, .venv
echo.
pause

echo.
echo [1/5] Deteniendo el programador...
schtasks /end /tn "%TASK%" >nul 2>&1
REM Solo procesos python cuya linea de comandos contiene programador.py; no toca otros python.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'programador\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
ping -n 4 127.0.0.1 >nul
if exist "%TARGET%\src\logs\programador.lock" del /F /Q "%TARGET%\src\logs\programador.lock"
echo       OK

echo [2/5] Copiando codigo...
REM robocopy: codigos de salida 0-7 = exito, 8 o mayor = error. Sin /PURGE: no borra nada del destino.
robocopy "%SRC%\src" "%TARGET%\src" /E /XD logs __pycache__ .pytest_cache /XF *.log *.pyc /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :err_copia
robocopy "%SRC%\scripts" "%TARGET%\scripts" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :err_copia
if exist "%SRC%\tests" (
    robocopy "%SRC%\tests" "%TARGET%\tests" /E /XD __pycache__ .pytest_cache /XF *.pyc /NFL /NDL /NJH /NJS /NP >nul
    if errorlevel 8 goto :err_copia
)
if exist "%SRC%\docs" (
    robocopy "%SRC%\docs" "%TARGET%\docs" /E /NFL /NDL /NJH /NJS /NP >nul
    if errorlevel 8 goto :err_copia
)
REM config: nunca se pisan los datos propios del servidor (credenciales y festivos adicionales).
REM selectors.json si se actualiza: refleja el DOM actual del portal.
robocopy "%SRC%\config" "%TARGET%\config" /E /XF employees.json festivos_adicionales.json /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :err_copia
if not exist "%TARGET%\config\festivos_adicionales.json" (
    if exist "%SRC%\config\festivos_adicionales.json" copy /Y "%SRC%\config\festivos_adicionales.json" "%TARGET%\config\" >nul
)
for %%F in (requirements.txt setup.bat setup.sh README.md LEEME_PRIMERO.txt exportar_exclude.txt .env.example actualizar_servidor.bat) do (
    if exist "%SRC%\%%F" copy /Y "%SRC%\%%F" "%TARGET%\" >nul
)
echo       OK

echo [3/5] Instalando dependencias...
if exist "%TARGET%\.venv\Scripts\python.exe" (
    set "PYTHON=%TARGET%\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
    echo       [WARN] No hay .venv en el destino; se usa el Python del sistema
)
"%PYTHON%" -m pip install -r "%TARGET%\requirements.txt" --quiet
if errorlevel 1 (
    echo       [WARN] Algunas dependencias no se pudieron instalar.
    echo              Revisa manualmente: "%PYTHON%" -m pip install -r requirements.txt
) else (
    echo       OK
)

echo [4/5] Verificando la tarea programada...
REM La tarea correcta arranca con el sistema (BootTrigger). Si no existe o es la antigua
REM (al iniciar sesion), se instala la nueva.
schtasks /query /tn "%TASK%" /xml 2>nul | findstr /C:"BootTrigger" >nul
if errorlevel 1 (
    echo       La tarea no existe o es la version antigua: instalando la nueva...
    call "%TARGET%\scripts\instalar_tarea_servidor.bat"
)

echo [5/5] Iniciando el programador...
schtasks /run /tn "%TASK%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se pudo iniciar la tarea "%TASK%".
    echo         Instalala con "%TARGET%\scripts\instalar_tarea_servidor.bat" y luego
    echo         ejecuta "%TARGET%\scripts\reiniciar_programador.bat".
    echo.
    pause
    exit /b 1
)
ping -n 8 127.0.0.1 >nul
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'programador\.py' }; if ($p) { Write-Host ('[OK] Programador en ejecucion (PID ' + (($p | ForEach-Object ProcessId) -join ', ') + ')') } else { Write-Host '[WARN] No se detecta el proceso. Revisa src\logs\servicio.log y src\logs\programador_*.log'; exit 1 }"

echo.
echo ================================================
echo   ACTUALIZACION COMPLETADA
echo ================================================
echo.
echo Verifica con: %TARGET%\scripts\ver_estado.bat
echo Log en vivo:  %TARGET%\scripts\ver_log_en_vivo.bat
echo.
pause
exit /b 0

:err_copia
echo.
echo [ERROR] Fallo el copiado de archivos ^(robocopy codigo %errorlevel%^).
echo         El programador quedo detenido. Revisa permisos y que no haya archivos en uso,
echo         y vuelve a ejecutar este script.
echo.
pause
exit /b 1
