@echo off
chcp 65001 >nul
title GeoVic Programador (vigilado)

:: Ruta al repo — ajustar si es necesario
set SCRIPT_DIR=%~dp0
set REPO_DIR=%SCRIPT_DIR%..
set PROG=%REPO_DIR%\src\programador.py

echo ========================================
echo  GeoVic Programador con auto-reinicio
echo ========================================
echo.

:loop
echo [%date% %time%] Iniciando programador...
python "%PROG%"
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [%date% %time%] Programador termino (codigo de salida: %EXIT_CODE%)

:: Salida 0 = Ctrl+C (apagado manual) — no reiniciar
if %EXIT_CODE% EQU 0 goto fin

echo Reiniciando en 30 segundos... (cierra esta ventana para cancelar)
timeout /t 30 /nobreak >nul
goto loop

:fin
echo.
echo Programador detenido manualmente.
pause
