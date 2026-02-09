# 🪟 Configurar Tarea Programada en Windows

## ⚠️ PROBLEMA COMÚN

Si configuras el programador como una **Tarea Programada de Windows** y:
- ❌ No genera logs
- ❌ No ejecuta marcajes
- ❌ Parece que no hace nada

Es porque la tarea necesita configuración especial.

---

## ✅ CONFIGURACIÓN CORRECTA

### **Opción 1: Ejecutar con Ventana Visible (RECOMENDADO)**

Esta es la forma MÁS SIMPLE y CONFIABLE:

1. **Abrir Programador de Tareas** (Task Scheduler)
   - Presiona `Win + R`
   - Escribe: `taskschd.msc`
   - Presiona Enter

2. **Crear Tarea Básica**
   - Clic derecho en "Biblioteca del Programador de tareas"
   - Seleccionar: **"Crear tarea..."** (NO "Crear tarea básica")

3. **Pestaña "General"**
   ```
   ✅ Nombre: GeoVictoria Programador
   ✅ Descripción: Marcaje automático de asistencia
   ⚠️ Configurar para: Windows 10/11
   ⚠️ Ejecutar solo cuando el usuario haya iniciado sesión
   ⚠️ Ejecutar con los privilegios más altos: NO (desmarcar)
   ```

4. **Pestaña "Desencadenadores"**
   - Clic en **"Nuevo..."**
   ```
   Iniciar la tarea: Al iniciar sesión
   Usuario específico: [tu usuario]
   ✅ Habilitado
   ```

5. **Pestaña "Acciones"**
   - Clic en **"Nueva..."**
   ```
   Acción: Iniciar un programa
   
   Programa o script:
   C:\Users\ealarconm\Documents\GeoVic\scripts\iniciar_programador.bat
   
   Iniciar en (opcional):
   C:\Users\ealarconm\Documents\GeoVic
   ```

6. **Pestaña "Condiciones"**
   ```
   ❌ Iniciar la tarea solo si el equipo está conectado a la alimentación de CA (desmarcar)
   ❌ Detener si el equipo deja de estar conectado a la alimentación de CA (desmarcar)
   ❌ Iniciar la tarea solo si el equipo está inactivo durante... (desmarcar)
   ✅ Activar la tarea al volver a conectarse a la red (marcar - útil si hay problemas de red)
   ```

7. **Pestaña "Configuración"**
   ```
   ✅ Permitir que la tarea se ejecute a petición
   ✅ Ejecutar la tarea lo antes posible después de perder una ejecución programada
   ❌ Si la tarea no se ejecuta correctamente, reiniciar cada: (desmarcar)
   ❌ Detener la tarea si se ejecuta más de: (desmarcar)
   ❌ Si la tarea ya se está ejecutando, aplicar la siguiente regla: No iniciar una nueva instancia
   ```

8. **Guardar**
   - Clic en **"Aceptar"**
   - Puede pedir tu contraseña de Windows

---

### **Opción 2: Ejecutar en Segundo Plano (AVANZADO)**

⚠️ Solo usa esta opción si entiendes las implicaciones de seguridad.

**Modificar el script `iniciar_programador.bat`:**

```batch
@echo off
REM Script para ejecutar el programador en segundo plano desde Task Scheduler

cd /d "%~dp0\.."

REM Verificar archivo .env
if not exist ".env" (
    echo ERROR: Archivo .env no encontrado > "%TEMP%\geovic_error.txt"
    exit /b 1
)

REM Ejecutar sin mostrar ventana (para Task Scheduler)
start /B pythonw src\programador.py > "src\logs\task_scheduler.log" 2>&1
```

**Configuración de Tarea:**
- En "General": ✅ **Ejecutar tanto si el usuario inició sesión como si no**
- ⚠️ Esto requerirá guardar tu contraseña en Task Scheduler

---

## 🔍 VERIFICAR QUE FUNCIONA

### **1. Probar la tarea manualmente:**
```powershell
# En PowerShell
schtasks /run /tn "GeoVictoria Programador"
```

### **2. Ver estado de la tarea:**
```powershell
schtasks /query /tn "GeoVictoria Programador" /v /fo list
```

### **3. Verificar logs:**
```powershell
# Ver últimas líneas del log de hoy
Get-Content "src\logs\programador_$(Get-Date -Format 'yyyyMMdd').log" -Tail 50
```

### **4. Ver registro de ejecuciones:**
```powershell
scripts\ver_estado_detallado.bat
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### **Problema: La tarea dice "Ejecutándose" pero no hace nada**

**Causa:** Múltiples instancias del programador corriendo.

**Solución:**
```powershell
# Matar todos los procesos de Python
taskkill /F /IM python.exe

# Esperar 5 segundos
Start-Sleep -Seconds 5

# Ejecutar reiniciar_programador.bat
scripts\reiniciar_programador.bat
```

### **Problema: No genera logs**

**Causa:** Permisos o ruta incorrecta.

**Solución:**
1. Verificar que la ruta en "Iniciar en" sea correcta
2. Ejecutar manualmente desde CMD:
   ```cmd
   cd C:\Users\ealarconm\Documents\GeoVic
   python src\programador.py
   ```
3. Si funciona manualmente pero no como tarea, revisar permisos de la carpeta

### **Problema: Se cierra inmediatamente**

**Causa:** Error en el código o dependencias faltantes.

**Solución:**
1. Ejecutar manualmente para ver el error:
   ```cmd
   scripts\iniciar_programador.bat
   ```
2. Verificar dependencias:
   ```cmd
   pip install -r requirements.txt
   playwright install chromium
   ```

---

## 📊 MONITOREO DIARIO

### **Crear script de verificación matutina:**

Guarda esto como `verificar_estado_matutino.bat`:

```batch
@echo off
echo ========================================
echo   VERIFICACION ESTADO GEOVICTORIA
echo ========================================
echo.

REM Verificar si el programador está corriendo
tasklist /FI "WINDOWTITLE eq Programador GeoVictoria*" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] Programador esta corriendo
) else (
    echo [ERROR] Programador NO esta corriendo
    echo.
    echo Desea iniciarlo ahora? (S/N)
    choice /C SN /N
    if errorlevel 2 goto :fin
    if errorlevel 1 call scripts\iniciar_programador.bat
)

echo.
echo ========================================
echo   MARCAJES DE HOY
echo ========================================
python scripts\verificar_estado.py

:fin
pause
```

---

## ✅ RECOMENDACIÓN FINAL

**Para máxima confiabilidad:**

1. ✅ **Usar Opción 1** (con ventana visible)
2. ✅ **Minimizar** la ventana (no cerrar)
3. ✅ **Verificar cada mañana** que el programador sigue corriendo
4. ✅ **Revisar logs** ocasionalmente
5. ✅ **Reiniciar solo cuando hagas cambios** al código

La ventana puede estar minimizada todo el día. No consume recursos significativos.

---

## 🔄 ¿CUÁNDO REINICIAR?

Solo ejecuta `reiniciar_programador.bat` cuando:
- 🔧 Actualizaste el código
- 🔑 Cambiaste credenciales en `.env`
- ⚙️ Modificaste horarios en `HorarioConfig`
- 🐛 Hay errores visibles en logs
- ❌ Los marcajes no se ejecutan

**NO es necesario reiniciar:**
- ✅ Cada día (el programador se reconfigura automáticamente a las 00:01)
- ✅ Si está funcionando correctamente
- ✅ Solo porque minimizaste la ventana
