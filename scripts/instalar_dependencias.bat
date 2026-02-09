@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ================================================
echo  Instalando Dependencias de GeoVictoria
echo ================================================
echo.

echo 📦 Verificando entorno virtual...
if exist ".venv\Scripts\activate.bat" (
    echo ✓ Entorno virtual encontrado
    echo.
    echo 📥 Instalando/Actualizando dependencias...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
) else (
    echo ⚠️  Entorno virtual no encontrado
    echo.
    echo 📥 Instalando dependencias globalmente...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
)

echo.
echo ================================================
echo  Instalación completada
echo ================================================
echo.
echo ✅ Dependencias instaladas:
echo    • playwright
echo    • python-dotenv
echo    • apscheduler
echo    • psutil
echo.

pause
