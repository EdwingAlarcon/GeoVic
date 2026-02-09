@echo off
chcp 65001 > nul
echo ================================================================================
echo 🔍 VERIFICADOR DE LOCK FILE - GeoVictoria
echo ================================================================================
echo.

cd /d "%~dp0.."
python scripts\verificar_lock_obsoleto.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ El programador puede iniciarse sin problemas
) else (
    echo.
    echo ⚠️  Revise el diagnóstico anterior
)

echo.
echo ================================================================================
pause
