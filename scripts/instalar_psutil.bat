@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ================================================
echo  Instalando psutil (dependencia faltante)
echo ================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    echo 📦 Usando entorno virtual...
    .venv\Scripts\python.exe -m pip install "psutil>=5.9.0"
) else (
    echo 📦 Instalando globalmente...
    python -m pip install "psutil>=5.9.0"
)

echo.
if %ERRORLEVEL% EQU 0 (
    echo ✅ psutil instalado correctamente
) else (
    echo ❌ Error instalando psutil
    echo.
    echo Intente manualmente:
    echo   python -m pip install psutil
)

echo.
pause
