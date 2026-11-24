@echo off
chcp 65001 >nul
REM Cifra con DPAPI las contrasenas en claro de config\employees.json.
REM EJECUTAR EN EL SERVIDOR: lo cifrado solo se descifra en el equipo donde se cifro.
REM Se puede repetir sin problema (las ya cifradas se dejan igual). No hace falta detener el programador.

cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
    echo [WARN] Entorno virtual no encontrado, usando Python del sistema
)

echo ================================================
echo   CIFRAR CONTRASENAS DE employees.json (DPAPI)
echo ================================================

%PYTHON% scripts\cifrar_credenciales.py %*

echo.
pause
