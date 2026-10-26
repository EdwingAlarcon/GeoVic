@echo off
chcp 65001 >nul
REM Monitor web de solo lectura del programador (abre el navegador en http://127.0.0.1:8765).
REM Deja esta ventana abierta mientras lo uses; Ctrl+C la cierra. No toca el portal ni modifica nada.
REM Para verlo desde otro equipo de la red:  monitor.bat --host 0.0.0.0 --token UNA_CLAVE_LARGA

cd /d "%~dp0.."

REM --- Detectar Python: venv si existe, sino sistema ---
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
    echo [WARN] Entorno virtual no encontrado, usando Python del sistema
)

echo ================================================
echo   MONITOR GEOVICTORIA  (solo lectura)
echo ================================================
echo Preparando (la primera vez tarda unos segundos)...

%PYTHON% scripts\monitor.py --abrir %*

echo.
pause
