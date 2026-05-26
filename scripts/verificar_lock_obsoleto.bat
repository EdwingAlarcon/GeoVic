@echo off
chcp 65001 > nul
echo ================================================================================
echo 🔍 VERIFICADOR DE LOCK FILE - GeoVictoria
echo ================================================================================
echo.

cd /d "%~dp0.."

REM --- Detectar Python: venv si existe, sino sistema ---
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

%PYTHON% scripts\verificar_lock_obsoleto.py

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
