@echo off
chcp 65001 >nul
REM Actualiza una instalacion existente de GeoVic en el servidor.
REM
REM USO: extraer GeoVic-Portable.zip en una carpeta temporal y dar doble clic a ESTE archivo.
REM Pregunta la carpeta del proyecto instalado (la recuerda: la proxima vez basta con Enter),
REM copia el codigo nuevo encima, limpia restos de versiones anteriores y reinicia el programador
REM y el monitor web (ventana "Monitor GeoVictoria", http://127.0.0.1:8765).
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
echo [1/5] Cerrando el programador y el monitor en marcha, con sus ventanas...
schtasks /end /tn "%TASK%" >nul 2>&1
REM Se cierran los procesos python Y las ventanas de consola (cmd) que los envuelven: si solo se mata el
REM python, la ventana "cmd /k" queda abierta y vacia y se acumula una mas en cada actualizacion. Tambien
REM las ventanas viejas ya acumuladas y la de "Log en vivo". Solo toca procesos del proyecto (por su linea de
REM comandos); no toca otros python ni este mismo actualizador.
powershell -NoProfile -Command "$yo = $PID; Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $yo -and ( ($_.Name -match '^(python|pythonw|cmd)(\.exe)?$' -and $_.CommandLine -match 'programador\.py|monitor\.py|\\monitor\.bat|\\iniciar_programador\.bat|\\ver_log_en_vivo\.bat') -or ($_.Name -match '^(powershell|pwsh)(\.exe)?$' -and $_.CommandLine -match 'programador_\*\.log') ) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('      cerrado: ' + $_.Name + ' PID ' + $_.ProcessId) }"
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
REM Scripts y docs retirados en versiones anteriores. robocopy no borra nada del destino, asi que
REM se eliminan aqui por nombre exacto: sobre todo los que mataban todos los python.exe
REM (detener_todas_instancias, corregir_problema_completo) no deben quedar en el servidor.
for %%F in (
    instalar_tarea_servidor.bat instalar_tarea_servidor.ps1 servicio_programador.bat
    configurar_tarea_windows.bat configurar_tarea_windows.ps1 ejecutar_tarea_programada.bat
    estado_tarea_programada.bat instalar_autoarranque.bat instalar_autoarranque.ps1
    desinstalar_autoarranque.bat detener_tarea_programada.bat detener_todas_instancias.bat
    corregir_problema_completo.bat diagnostico_completo.bat diagnostico_estado.bat
    diagnostico_estado_completo.py verificar_lock_obsoleto.bat verificar_lock_obsoleto.py
    validar_optimizaciones.py prueba_verificacion_estado.py marcar_salida_ahora.py
    instalar_psutil.bat instalar_dependencias.bat iniciar_programador_vigilado.bat
    SOLUCION_HOY.bat habilitar_tareas.bat iniciar_sin_reiniciar.bat
    reiniciar_con_correcciones.bat reiniciar_optimizado.bat ver_estado_detallado.bat
    modo_oculto.bat iniciar_oculto.bat
) do (
    if exist "%TARGET%\scripts\%%F" (
        del /F /Q "%TARGET%\scripts\%%F"
        echo       eliminado scripts\%%F
    )
)
REM El modo oculto se retiro: se borra su marcador para que no quede configuracion muerta.
if exist "%TARGET%\config\modo_oculto.flag" (
    del /F /Q "%TARGET%\config\modo_oculto.flag"
    echo       eliminado config\modo_oculto.flag
)
for %%F in (CONFIGURAR_TAREA_WINDOWS.md INICIAR_SIN_REINICIAR.md INSTALACION.md) do (
    if exist "%TARGET%\docs\%%F" (
        del /F /Q "%TARGET%\docs\%%F"
        echo       eliminado docs\%%F
    )
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

echo [4/5] Iniciando el programador y el monitor en ventanas nuevas ^(navegador visible^)...
REM Una ventana de consola por proceso, con el navegador visible en tu sesion. No se crea ninguna Tarea
REM Programada. El monitor abre solo la pagina de monitoreo en el navegador: http://127.0.0.1:8765
start "Programador GeoVictoria" /D "%TARGET%" cmd /k ""%PYTHON%" src\programador.py"
start "Monitor GeoVictoria" /D "%TARGET%" cmd /k ""%PYTHON%" scripts\monitor.py --abrir"
ping -n 8 127.0.0.1 >nul

echo [5/5] Verificando...
powershell -NoProfile -Command "$m = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'monitor\.py' }; if ($m) { Write-Host '[OK] Monitor en http://127.0.0.1:8765' } else { Write-Host '[AVISO] No se detecta el monitor; abrelo con scripts\monitor.bat (el programador no depende de el).' }"
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'programador\.py' }; if ($p) { Write-Host ('[OK] Programador en ejecucion (PID ' + (($p | ForEach-Object ProcessId) -join ', ') + ')') } else { Write-Host '[WARN] No se detecta el proceso. Mira la ventana Programador GeoVictoria.'; exit 1 }"

echo.
echo ================================================
echo   ACTUALIZACION COMPLETADA
echo ================================================
echo.
echo Deja abiertas las ventanas "Programador GeoVictoria" y "Monitor GeoVictoria" ^(puedes minimizarlas, no cerrarlas^).
echo Monitor en vivo ^(con botones para reiniciar/detener^): http://127.0.0.1:8765
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
