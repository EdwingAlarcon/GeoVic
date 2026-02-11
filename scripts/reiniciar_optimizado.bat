@echo off
echo ================================================================================
echo 🚀 REINICIAR CON OPTIMIZACIONES APLICADAS
echo ================================================================================
echo.
echo OPTIMIZACIONES APLICADAS:
echo   ✅ Sistema de caché implementado (-80%% consultas redundantes)
echo   ✅ Timeouts optimizados (60s → 30s)
echo   ✅ Logging reducido (-60%% volumen)
echo   ✅ Código consolidado (-150 líneas duplicadas)
echo.
echo MEJORAS ESPERADAS:
echo   📊 Tiempo de verificación: 40-60s → 10-15s (-70%%)
echo   📊 Consultas por hora: 4-5 → 1 (-80%%)
echo   📊 Consumo de recursos: -70%%
echo.
pause

echo.
echo 🛑 Deteniendo instancias previas...
call "%~dp0detener_todas_instancias.bat"

echo.
echo ⏳ Esperando 3 segundos...
timeout /t 3 /nobreak >nul

echo.
echo 🚀 Iniciando programador OPTIMIZADO...
cd /d "%~dp0.."
start "GeoVictoria [OPTIMIZADO v2.0]" python src/programador.py

echo.
echo ✅ Programador optimizado iniciado
echo.
echo 💡 Monitorea las mejoras:
echo    - Logs más limpios en src/logs/
echo    - Verificaciones más rápidas (10-15s vs 40-60s antes)
echo    - Menos consumo de recursos
echo.
echo 📊 Valida optimizaciones:
echo    python scripts\validar_optimizaciones.py
echo.
pause
