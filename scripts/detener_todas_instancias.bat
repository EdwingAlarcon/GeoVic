@echo off
chcp 65001 > nul
echo ================================================
echo  Deteniendo todas las instancias del programador
echo ================================================
echo.

echo Buscando procesos de Python relacionados con programador...
tasklist /FI "IMAGENAME eq python.exe" /V | findstr /I "programador"

echo.
echo Deteniendo procesos...
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /NH ^| findstr /I "python"') do (
    echo Deteniendo PID %%i...
    taskkill /PID %%i /F >nul 2>&1
)

echo.
echo Eliminando archivo de lock...
if exist "%~dp0..\src\logs\programador.lock" (
    del /F "%~dp0..\src\logs\programador.lock"
    echo ✓ Lock file eliminado
) else (
    echo ℹ Lock file no encontrado
)

echo.
echo ================================================
echo  Proceso completado
echo ================================================
echo.
echo Presione cualquier tecla para cerrar...
pause > nul
