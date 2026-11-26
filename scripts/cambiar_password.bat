@echo off
chcp 65001 >nul
REM Cambia la contrasena de UN empleado: la pide sin mostrarla, prueba el login (sin marcar)
REM y la guarda CIFRADA en config\employees.json. EJECUTAR EN EL SERVIDOR.
REM Uso: cambiar_password.bat          (lista los empleados y pregunta cual)
REM      cambiar_password.bat emp6     (por id o por parte del nombre)
REM Despues hay que reiniciar el programador (reiniciar_programador.bat) lejos de una hora de marcaje.

cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
    echo [WARN] Entorno virtual no encontrado, usando Python del sistema
)

echo ================================================
echo   CAMBIAR LA CONTRASENA DE UN EMPLEADO
echo ================================================

%PYTHON% scripts\cambiar_password.py %*

echo.
pause
