# 🔧 SOLUCIÓN: Marcajes Duplicados o Repetidos

## Problema Identificado

Se detectaron las siguientes causas de marcajes duplicados o repetidos:

### 1. **Múltiples Instancias del Programador**
- Varios procesos del programador ejecutándose simultáneamente
- Cada instancia intenta marcar entrada/salida al mismo tiempo
- **Causado por**: Iniciar el programador múltiples veces sin detener instancias anteriores

### 2. **Sin Protección contra Ejecuciones Duplicadas**
- Las funciones de marcaje no verificaban si ya se ejecutaron
- Permitía que múltiples llamadas marcaran entrada/salida en el mismo día
- **Causado por**: Falta de validación temprana en el código

### 3. **Registro de Ejecuciones Corrupto**
- El archivo `registro_ejecuciones.json` puede contener datos incorrectos
- Entrada y salida marcadas a la misma hora (ejemplo: ambas a las 7 AM)
- **Causado por**: Ejecuciones previas con errores o marcajes manuales

## Soluciones Implementadas

### ✅ 1. Sistema de Lock File
- **Qué hace**: Previene que múltiples instancias del programador se ejecuten
- **Cómo funciona**: Crea un archivo `programador.lock` con el PID del proceso activo
- **Beneficio**: Solo UNA instancia puede ejecutarse a la vez

### ✅ 2. Protección en Funciones de Marcaje
- **Qué hace**: Verifica si el marcaje ya se ejecutó ANTES de intentar marcarlo
- **Cómo funciona**: Revisa `registro_ejecuciones.json` al inicio de cada función
- **Beneficio**: Evita marcajes duplicados incluso si se llama múltiples veces

### ✅ 3. Scripts de Limpieza
Se crearon dos scripts para resolver problemas existentes:

#### `detener_todas_instancias.bat`
- Detiene todos los procesos Python (programador)
- Elimina el archivo de lock
- **Usar cuando**: Multiple instancias están corriendo

#### `limpiar_registro_hoy.bat`
- Elimina el registro de ejecuciones del día actual
- Permite que los marcajes se ejecuten normalmente en sus horarios
- **Usar cuando**: El registro tiene datos incorrectos (entrada y salida en horarios incorrectos)

## 🚀 Pasos para Corregir el Problema Actual

### Paso 1: Detener Todas las Instancias
```cmd
cd C:\Users\user\Documents\Repo\GeoVic
scripts\detener_todas_instancias.bat
```

### Paso 2: Limpiar el Registro de Hoy (si tiene datos incorrectos)
```cmd
scripts\limpiar_registro_hoy.bat
```
**NOTA**: Esto eliminará el registro de hoy, permitiendo que los marcajes se ejecuten en sus horarios normales.

### Paso 3: Verificar que NO hay procesos del programador
```powershell
Get-Process | Where-Object {$_.ProcessName -match "python"}
```
**Resultado esperado**: No debería haber procesos Python relacionados con el programador.

### Paso 4: Iniciar el Programador (UNA SOLA VEZ)
```cmd
scripts\iniciar_programador.bat
```

### Paso 5: Verificar que Solo Hay UNA Instancia
```powershell
Get-Process | Where-Object {$_.ProcessName -match "python"} | Format-Table ProcessName, Id, StartTime
```
**Resultado esperado**: Solo UN proceso Python.

## 📋 Verificación del Estado

Para verificar que todo está funcionando correctamente:

```cmd
scripts\ver_estado_detallado.bat
```

Revise:
- ✅ Solo UNA instancia del programador corriendo
- ✅ Archivo de lock existe con PID correcto
- ✅ Próximas ejecuciones programadas correctamente:
  - Entrada L-V: 07:00
  - Salida L-V: 17:00
  - Entrada Sáb: 07:00
  - Salida Sáb: 13:00
  - Verificación periódica: Cada hora en punto

## 🔍 Cómo Identificar el Problema en el Futuro

### Síntomas de Múltiples Instancias
- Varios procesos Python en el administrador de tareas
- Múltiples ventanas del programador abiertas
- Mensajes de error sobre lock file al iniciar

### Síntomas de Marcajes Duplicados
- Entrada y salida marcadas a la misma hora en `registro_ejecuciones.json`
- Múltiples marcajes en GeoVictoria en el mismo día
- Logs muestran ejecuciones duplicadas

### Cómo Revisar el Registro
```cmd
notepad src\logs\registro_ejecuciones.json
```

**Registro CORRECTO** (ejemplo viernes):
```json
{
  "2026-02-09": {
    "ENTRADA SEMANA (L-V)": {
      "ejecutado": true,
      "hora": "2026-02-09T07:05:14",
      "variacion_minutos": 5
    },
    "SALIDA SEMANA (L-V)": {
      "ejecutado": true,
      "hora": "2026-02-09T17:08:20",
      "variacion_minutos": 8
    }
  }
}
```

**Registro INCORRECTO** (ambos a las 7 AM):
```json
{
  "2026-02-09": {
    "ENTRADA SEMANA (L-V)": {
      "ejecutado": true,
      "hora": "2026-02-09T07:05:14"
    },
    "SALIDA SEMANA (L-V)": {
      "ejecutado": true,
      "hora": "2026-02-09T07:06:20"  ← ❌ INCORRECTO
    }
  }
}
```

## 🛡️ Prevención

Para evitar este problema en el futuro:

1. **Nunca iniciar el programador múltiples veces**
   - Verificar que no está corriendo antes de iniciarlo
   - Usar `scripts\ver_estado.bat` para verificar

2. **Usar los scripts proporcionados**
   - `iniciar_programador.bat` - Inicia el programador de forma segura
   - `detener_tarea_programada.bat` - Detiene correctamente
   - `ver_estado.bat` - Verifica el estado

3. **Revisar logs regularmente**
   - Ubicación: `src\logs\programador_YYYYMMDD.log`
   - Buscar: "⚠️", "❌", "ERROR" para identificar problemas

4. **Monitorear el registro de ejecuciones**
   - Ubicación: `src\logs\registro_ejecuciones.json`
   - Verificar que las horas de entrada y salida son correctas

## 📞 Soporte

Si el problema persiste:

1. Revise los logs más recientes
2. Ejecute `scripts\diagnostico_completo.bat`
3. Verifique que solo hay una instancia del programador
4. Asegúrese de que el registro de ejecuciones es correcto

---

**Última actualización**: 9 de febrero de 2026
**Versión**: 2.0
