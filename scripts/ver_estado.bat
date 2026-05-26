@echo off
chcp 65001 >nul
echo ========================================
echo   ESTADO DE MARCAJES GEOVICTORIA
echo ========================================
echo.

cd /d "%~dp0\.."

REM --- Detectar Python: venv si existe, sino sistema ---
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

REM Obtener fecha actual en formato YYYYMMDD
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set fecha_log=%datetime:~0,8%

echo Fecha: %DATE%
echo Hora:  %TIME:~0,8%
echo.

echo ========================================
echo REGISTRO DE EJECUCIONES DE HOY:
echo ========================================
cd /d "%~dp0\..\src\logs"

REM Leer todos los registros de empleados (single y multi)
%PYTHON% -c "
import json, sys, glob
from datetime import date
from pathlib import Path

log_dir = Path('.')
hoy = str(date.today())
archivos = list(log_dir.glob('registro_*.json')) + list(log_dir.glob('registro_ejecuciones.json'))

if not archivos:
    print('No hay archivos de registro.')
    sys.exit(0)

total = 0
for archivo in sorted(archivos):
    try:
        data = json.loads(archivo.read_text(encoding='utf-8'))
        registros = data.get(hoy, {})
        if registros:
            emp = archivo.stem.replace('registro_', '').replace('_', ' ').replace('ejecuciones', 'default')
            print(f'  Empleado: {emp}')
            for k, v in registros.items():
                print(f'    OK  {k}')
                print(f'        Hora: {v[\"hora\"]}')
            total += len(registros)
    except Exception as e:
        print(f'  Error leyendo {archivo.name}: {e}')

if total == 0:
    print('  No hay marcajes registrados para hoy')
"

echo.
cd /d "%~dp0\..\src\logs"

echo ========================================
echo ULTIMAS LINEAS DEL LOG DEL PROGRAMADOR:
echo ========================================
powershell -Command "Get-Content 'programador_%fecha_log%.log' -Tail 20 -ErrorAction SilentlyContinue | Select-String -Pattern 'Marcaje|completado|Error|FESTIVO|DOMINGO|Pendiente' | ForEach-Object { $_.Line }"

echo.
echo ========================================
echo ALERTAS RECIENTES:
echo ========================================
if exist "alertas.log" (
    powershell -Command "Get-Content 'alertas.log' -Tail 10 -ErrorAction SilentlyContinue | ForEach-Object { $_.Line }"
) else (
    echo   Sin alertas registradas
)

echo.
echo ========================================
pause
