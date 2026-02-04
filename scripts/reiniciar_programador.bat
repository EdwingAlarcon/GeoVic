@echo off
echo ============================================
echo   REINICIANDO PROGRAMADOR GEOVICTORIA
echo ============================================
echo.

echo [1/3] Deteniendo programador actual...
taskkill /F /FI "WINDOWTITLE eq Programador GeoVictoria*" >nul 2>&1
taskkill /F /IM python.exe /FI "MEMUSAGE gt 10000" >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Limpiando procesos...
timeout /t 1 /nobreak >nul

echo [3/3] Iniciando programador con nueva version...
echo.
start "Programador GeoVictoria" cmd /k "cd /d %~dp0..\ && python src\programador.py"

echo.
echo ============================================
echo   PROGRAMADOR REINICIADO
echo ============================================
echo   Se abrio una nueva ventana con el programador
echo   Puedes cerrar esta ventana
echo ============================================
pause
