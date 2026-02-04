@echo off
chcp 65001 >nul
echo ========================================
echo 📊 ESTADO DE MARCAJES GEOVICTORIA
echo ========================================
echo.

REM Obtener fecha actual en formato YYYYMMDD
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set fecha_log=%datetime:~0,8%

echo 📅 Fecha: %DATE%
echo ⏰ Hora: %TIME:~0,8%
echo.

echo ========================================
echo 📝 REGISTRO DE EJECUCIONES DE HOY:
echo ========================================
cd /d "%~dp0\..\src\logs"

REM Mostrar registro JSON formateado
python -c "import json; import sys; from datetime import date; data = json.load(open('registro_ejecuciones.json', encoding='utf-8')); hoy = str(date.today()); print('Hoy:', hoy); print(); registros = data.get(hoy, {}); [print(f'✅ {k}:\n   🕐 Hora: {v[\"hora\"]}\n   🎲 Variación: {v.get(\"variacion_minutos\", 0):+d} minutos\n') if registros else None for k, v in registros.items()] if registros else print('❌ No hay marcajes registrados para hoy\n')"

echo ========================================
echo 📋 ÚLTIMAS LÍNEAS DEL LOG DEL PROGRAMADOR:
echo ========================================
powershell -Command "Get-Content 'programador_%fecha_log%.log' -Tail 20 -ErrorAction SilentlyContinue | Select-String -Pattern 'ejecut|completado|Error|Intento de marcaje|FESTIVO|DOMINGO' | ForEach-Object { $_.Line }"

echo.
echo ========================================
echo 📋 ÚLTIMAS LÍNEAS DEL LOG DE GEOVICTORIA:
echo ========================================
powershell -Command "Get-Content 'geovictoria_%fecha_log%.log' -Tail 15 -ErrorAction SilentlyContinue | Select-String -Pattern 'ejecut|Login|exitoso|Error|Marcaje' | ForEach-Object { $_.Line }"

echo.
echo ========================================
pause
