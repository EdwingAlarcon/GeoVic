@echo off
chcp 65001 >nul
title GeoVic - Log en vivo del programador
REM Muestra en vivo el log del programador (solo lectura; cerrar la ventana no afecta al programador).
REM El nombre del log se fija cuando arranca el proceso, asi que un programador que lleva dias
REM corriendo escribe en el archivo de su fecha de arranque: se sigue el modificado mas recientemente.

cd /d "%~dp0\.."

if not exist "src\logs" (
    echo No existe src\logs: el programador aun no ha corrido.
    echo.
    pause
    exit /b 1
)

echo ============================================
echo   LOG EN VIVO - PROGRAMADOR GEOVICTORIA
echo   Ctrl+C o cerrar la ventana para salir
echo   (el programador sigue corriendo)
echo ============================================
echo.

powershell -NoProfile -Command "$f = Get-ChildItem 'src\logs\programador_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if (-not $f) { Write-Host 'No hay logs del programador todavia.'; exit 1 }; Write-Host ('Archivo: ' + $f.Name + '  (ultima escritura: ' + $f.LastWriteTime + ')'); Write-Host ''; Get-Content $f.FullName -Encoding UTF8 -Tail 30 -Wait"

echo.
pause
