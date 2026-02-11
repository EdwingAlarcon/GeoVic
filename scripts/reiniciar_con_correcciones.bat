@echo off
echo ================================================================================
echo 🔄 REINICIAR PROGRAMADOR CON CORRECCIONES
echo ================================================================================
echo.
echo Este script:
echo 1. Detiene cualquier instancia previa del programador
echo 2. Reinicia el programador con el código corregido
echo.
pause

echo.
echo 🛑 Deteniendo instancias previas...
call "%~dp0detener_todas_instancias.bat"

echo.
echo ⏳ Esperando 3 segundos...
timeout /t 3 /nobreak >nul

echo.
echo 🚀 Iniciando programador con correcciones...
cd /d "%~dp0.."
start "GeoVictoria Programador [CORREGIDO]" python src/programador.py

echo.
echo ✅ Programador reiniciado
echo.
echo 💡 Para verificar que está funcionando:
echo    - Revisa los logs en src/logs/
echo    - Ejecuta: scripts\ver_estado_detallado.bat
echo.
pause
