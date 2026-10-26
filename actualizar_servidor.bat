@echo off
chcp 65001 >nul
REM Actualiza una instalacion existente de GeoVic en el servidor.
REM
REM USO: extraer GeoVic-Portable.zip en una carpeta temporal y dar doble clic a ESTE archivo.
REM Pregunta la carpeta del proyecto instalado (la recuerda: la proxima vez basta con Enter),
REM copia el codigo nuevo encima, limpia restos de versiones anteriores y reinicia el programador.
REM
REM Conserva: .env, config\employees.json, config\festivos_adicionales.json, src\logs, .venv
REM No requiere Administrador: el programador queda en una ventana de TU sesion (navegador visible).

set "TASK=GeoVictoria Programador"

echo.
echo ================================================
echo   ACTUALIZAR GEOVICTORIA (servidor)
echo ================================================
echo.

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

REM --- Destino: carpeta del proyecto instalado (se recuerda la ultima usada: basta con Enter) ---
echo Origen (zip extraido): %SRC%
echo.
set "DESTFILE=%LOCALAPPDATA%\GeoVic\destino.txt"
set "DEFAULT="
if exist "%DESTFILE%" set /p DEFAULT=<"%DESTFILE%"
set "TARGET="
if defined DEFAULT (
    set /p "TARGET=Carpeta del proyecto instalado [%DEFAULT%] - Enter para usarla: "
) else (
    set /p "TARGET=Carpeta del proyecto instalado (ej: C:\GeoVic): "
)
if defined TARGET set "TARGET=%TARGET:"=%"
if not defined TARGET set "TARGET=%DEFAULT%"
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

if not exist "%LOCALAPPDATA%\GeoVic" mkdir "%LOCALAPPDATA%\GeoVic" >nul 2>&1
>"%DESTFILE%" echo %TARGET%

echo.
echo Destino: %TARGET%
echo Se conservan: .env, config\employees.json, config\festivos_adicionales.json, src\logs, .venv
echo.
echo [1/5] Deteniendo el programador...
schtasks /end /tn "%TASK%" >nul 2>&1
REM Solo procesos python cuya linea de comandos contiene programador.py; no toca otros python.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'programador\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
ping -n 4 127.0.0.1 >nul
if exist "%TARGET%\src\logs\programador.lock" del /F /Q "%TARGET%\src\logs\programador.lock"

REM Limpieza automatica de la tarea "arranque sin sesion" (S4U) que instalo una version anterior:
REM correria el navegador sin escritorio (no abre ventana) y chocaria con el programador de esta ventana.
schtasks /query /tn "%TASK%" /xml 2>nul | findstr /C:"BootTrigger" >nul
if not errorlevel 1 (
    echo       Quitando la tarea de arranque sin sesion de una version anterior ^(pedira permiso de Administrador^)...
    powershell -NoProfile -Command "Start-Process schtasks -ArgumentList '/delete','/tn','%TASK%','/f' -Verb RunAs -Wait" >nul 2>&1
    schtasks /query /tn "%TASK%" >nul 2>&1
    if not errorlevel 1 echo       [AVISO] No se pudo quitar la tarea. Ejecuta scripts\eliminar_tarea_programada.bat como Administrador.
)
for %%F in (instalar_tarea_servidor.bat instalar_tarea_servidor.ps1 servicio_programador.bat) do (
    if exist "%TARGET%\scripts\%%F" del /F /Q "%TARGET%\scripts\%%F"
)
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

echo [4/5] Iniciando el programador en una ventana nueva (navegador visible)...
REM Igual que antes: ventana de consola propia, con el navegador visible en tu sesion.
REM No se crea ni se modifica ninguna Tarea Programada.
start "Programador GeoVictoria" /D "%TARGET%" cmd /k ""%PYTHON%" src\programador.py"
ping -n 8 127.0.0.1 >nul

echo [5/5] Verificando...
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'programador\.py' }; if ($p) { Write-Host ('[OK] Programador en ejecucion (PID ' + (($p | ForEach-Object ProcessId) -join ', ') + ')') } else { Write-Host '[WARN] No se detecta el proceso. Mira la ventana Programador GeoVictoria.'; exit 1 }"

echo.
echo ================================================
echo   ACTUALIZACION COMPLETADA
echo ================================================
echo.
echo Deja abierta la ventana "Programador GeoVictoria" (puedes minimizarla, no cerrarla).
echo Verifica con: %TARGET%\scripts\ver_estado.bat
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
