# GUÍA: Iniciar Sistema SIN REINICIAR Servidor

## 🚀 Inicio Rápido (3 pasos)

### PASO 1: Habilitar Tareas Programadas
```cmd
# Ejecutar como ADMINISTRADOR:
scripts\habilitar_tareas.bat
```

### PASO 2: Iniciar Programador Manualmente
```cmd
# Ejecutar (NO necesita ser administrador):
scripts\iniciar_sin_reiniciar.bat
```

### PASO 3: Verificar que Funciona
```cmd
# Ejecutar:
scripts\diagnostico_estado.bat
```

---

## 📋 Alternativa Manual (Paso a Paso)

### 1. Habilitar Tareas (Como Administrador)
```powershell
# Abrir PowerShell como Administrador y ejecutar:
schtasks /Change /TN "GeoVictoria" /Enable
schtasks /Change /TN "GeoVictoria Marcajes Automaticos" /Enable
```

### 2. Limpiar Procesos Anteriores
```powershell
# Matar procesos anteriores del programador (si existen):
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -like "*programador*"} | Stop-Process -Force

# Eliminar lock file:
Remove-Item "src\logs\programador.lock" -Force -ErrorAction SilentlyContinue
```

### 3. Iniciar Programador en Segundo Plano
```powershell
# Opción A: Ventana minimizada
Start-Process python -ArgumentList "src\programador.py" -WindowStyle Minimized

# Opción B: Como proceso oculto
Start-Process python -ArgumentList "src\programador.py" -WindowStyle Hidden -NoNewWindow
```

### 4. Verificar que Está Corriendo
```powershell
# Ver procesos de Python:
Get-Process python | Select-Object Id, ProcessName, StartTime

# Ver logs en tiempo real:
Get-Content "src\logs\programador_$(Get-Date -Format 'yyyyMMdd').log" -Wait -Tail 20
```

---

## 🔍 Verificación del Sistema

### Verificar Estado de Tareas
```powershell
Get-ScheduledTask -TaskName "GeoVictoria*" | Select-Object TaskName, State, LastRunTime, NextRunTime | Format-Table
```

**Resultado esperado:**
```
TaskName                          State  LastRunTime         NextRunTime
--------                          -----  -----------         -----------
GeoVictoria                       Ready  [fecha]             [próxima]
GeoVictoria Marcajes Automáticos  Ready  [fecha]             [próxima]
```

### Verificar Programador Corriendo
```powershell
Get-Process python | Where-Object {(Get-Date) - $_.StartTime -lt [TimeSpan]::FromHours(1)}
```

Si muestra procesos de Python iniciados recientemente → ✅ Está corriendo

### Ver Logs en Tiempo Real
```powershell
# Abrir en nueva ventana:
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Get-Content 'src\logs\programador_$(Get-Date -Format 'yyyyMMdd').log' -Wait -Tail 20"
```

---

## ⚡ Script Todo-en-Uno

He creado: **`scripts\iniciar_sin_reiniciar.bat`**

Este script hace TODO automáticamente:
1. ✅ Verifica tareas programadas
2. ✅ Detiene instancias anteriores
3. ✅ Limpia lock file
4. ✅ Inicia programador en segundo plano
5. ✅ Te muestra cómo verificar que funciona

**Uso:**
```cmd
# Doble clic en:
scripts\iniciar_sin_reiniciar.bat
```

---

## 🔄 Mantener el Programador Corriendo

### Opción 1: Dejar Ventana Minimizada
```cmd
start "GeoVictoria" /MIN python src\programador.py
```
- ✅ Fácil de monitorear
- ✅ Se puede cerrar si es necesario
- ⚠️ Si cierras la ventana, se detiene

### Opción 2: Usar Tarea Programada (Recomendado)
```powershell
# Iniciar la tarea programada manualmente (sin esperar a reiniciar):
Start-ScheduledTask -TaskName "GeoVictoria"
```
- ✅ Corre en segundo plano
- ✅ No se cierra accidentalmente
- ✅ Se reinicia automáticamente si el servidor se reinicia después

### Opción 3: Servicio Windows (Avanzado)
Si quieres que corra como servicio de Windows, puedo crear un script para eso.

---

## 📊 Monitoreo Continuo

### Ver Logs Actuales
```powershell
# Ver últimas 50 líneas:
Get-Content "src\logs\programador_$(Get-Date -Format 'yyyyMMdd').log" -Tail 50

# Seguir logs en tiempo real:
Get-Content "src\logs\programador_$(Get-Date -Format 'yyyyMMdd').log" -Wait
```

### Verificar Registro de Ejecuciones
```powershell
python -c "import json; print(json.dumps(json.load(open('src/logs/registro_ejecuciones.json')), indent=2))"
```

### Verificar Próxima Ejecución
```cmd
scripts\diagnostico_estado.bat
```

---

## ⚠️ Solución de Problemas

### Si el Programador No Inicia
```powershell
# 1. Verificar errores en logs:
Get-Content "src\logs\programador_$(Get-Date -Format 'yyyyMMdd').log" | Select-String "ERROR"

# 2. Verificar lock file:
Test-Path "src\logs\programador.lock"

# 3. Eliminar lock si existe:
Remove-Item "src\logs\programador.lock" -Force

# 4. Intentar nuevamente:
python src\programador.py
```

### Si Las Tareas Están Deshabilitadas
```cmd
# Ejecutar como ADMINISTRADOR:
scripts\habilitar_tareas.bat
```

---

## 🎯 Resumen Ejecutivo

**Para iniciar SIN reiniciar el servidor:**

```cmd
# 1. Como ADMINISTRADOR (una sola vez):
scripts\habilitar_tareas.bat

# 2. Como usuario normal:
scripts\iniciar_sin_reiniciar.bat

# 3. Verificar:
scripts\diagnostico_estado.bat
```

**¡Listo!** El sistema está corriendo sin necesidad de reiniciar. 🚀

---

**Última actualización**: 11 de Febrero de 2026
