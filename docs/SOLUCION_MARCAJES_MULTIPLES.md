# Solución al Problema de Múltiples Marcajes

## Problema Identificado

El sistema estaba marcando **múltiples entradas y salidas en el mismo día**, incluso marcando salida ANTES que entrada, lo cual no tiene sentido lógico.

### Análisis del Problema

Al revisar los logs del 9 de febrero de 2026, se encontró:

```json
"2026-02-09": {
  "SALIDA SEMANA (L-V)": {
    "ejecutado": true,
    "hora": "2026-02-09T17:10:21",
    "variacion_minutos": 10
  },
  "ENTRADA SEMANA (L-V)": {
    "ejecutado": true,
    "hora": "2026-02-09T17:12:15",
    "variacion_minutos": 12
  }
}
```

**La SALIDA se marcó ANTES que la ENTRADA** - esto es incorrecto.

### Causas Raíz Encontradas

1. **Falta de Validación de Orden Lógico**
   - Las funciones `salida_semana()` y `salida_sabado()` NO verificaban si existía una entrada previa antes de marcar salida
   - Esto permitía marcar salida sin entrada, lo cual GeoVictoria aceptaba como el primer marcaje del día

2. **Lock Files Obsoletos**
   - Se encontró un lock file de un proceso muerto (PID 9916)
   - Esto puede causar problemas al iniciar el programador

3. **Múltiples Reinicios**
   - El programador se reinició 3 veces el mismo día
   - Esto aumenta la probabilidad de marcajes duplicados o incorrectos

## Soluciones Aplicadas

### 1. Validación de Entrada Previa en Funciones de Salida

**Archivo modificado:** `src/programador.py`

Se agregó validación en las funciones `salida_semana()` y `salida_sabado()`:

```python
def salida_semana():
    # PROTECCIÓN 1: Verificar si ya se ejecutó antes de hacer nada
    if ya_se_ejecuto_hoy("SALIDA SEMANA (L-V)"):
        logger.info("⏭️ SALIDA SEMANA (L-V) ya ejecutada hoy - Omitiendo")
        return
    
    # PROTECCIÓN 2: Verificar que existe entrada previa (orden lógico)
    if not ya_se_ejecuto_hoy("ENTRADA SEMANA (L-V)"):
        logger.warning("⚠️ SALIDA SEMANA (L-V) omitida - No hay entrada previa registrada")
        logger.warning("   • No se puede marcar salida sin haber marcado entrada primero")
        logger.warning("   • La verificación periódica intentará corregir esto más tarde")
        return
    
    # ... resto del código
```

Ahora las funciones de salida:
- ✅ Verifican que no se haya ejecutado salida ya
- ✅ **NUEVO:** Verifican que exista entrada previa
- ✅ Solo entonces calculan variación y ejecutan marcaje

### 2. Script de Verificación de Lock Obsoletos

**Archivos creados:**
- `scripts/verificar_lock_obsoleto.py`
- `scripts/verificar_lock_obsoleto.bat`

Estos scripts:
- Detectan lock files de procesos muertos
- Los limpian automáticamente si el proceso no existe
- Alertan si hay un proceso real corriendo

### 3. Limpieza del Registro

Se eliminó el registro incorrecto del día 2026-02-09 para permitir que el sistema intente marcar correctamente si es necesario.

## Cómo Prevenir el Problema en el Futuro

### Antes de Iniciar el Programador

1. **Verificar lock files obsoletos:**
   ```
   scripts\verificar_lock_obsoleto.bat
   ```

2. **Detener instancias previas:**
   ```
   scripts\detener_todas_instancias.bat
   ```

3. **Iniciar el programador:**
   ```
   scripts\iniciar_programador.bat
   ```

### Monitoreo Regular

- Revise los logs en `src/logs/` regularmente
- Verifique que solo haya UN proceso del programador corriendo:
  ```
  scripts\ver_estado_detallado.bat
  ```

## Comportamiento Esperado Ahora

### Escenario 1: PC Encendido Tarde (Después de Hora de Entrada)

1. A las 17:00, `salida_semana()` se ejecuta
2. Verifica si hay entrada previa → NO hay
3. **Se omite el marcaje de salida** ✅
4. La verificación periódica detecta que falta la entrada
5. Si aún es antes de 12:00 PM, marca la entrada
6. Luego puede marcar la salida

### Escenario 2: Operación Normal

1. A las 07:00, `entrada_semana()` se ejecuta
2. Marca la entrada correctamente
3. A las 17:00, `salida_semana()` se ejecuta  
4. Verifica que hay entrada previa → SÍ hay
5. Marca la salida correctamente

### Escenario 3: PC Encendido Muy Tarde (Después de 12:00 PM)

1. La verificación periódica detecta que falta la entrada
2. Verifica la hora actual → Después de 12:00 PM
3. **Omite marcar entrada** (demasiado tarde)
4. A las 17:00, `salida_semana()` se ejecuta
5. Verifica entrada previa → NO hay
6. **Omite marcar salida** (sin entrada previa)
7. Resultado: No se hace ningún marcaje ese día (correcto)

## Resultado

Con estos cambios, el sistema ahora:

- ✅ **NUNCA** marcará salida sin entrada previa
- ✅ Respeta el orden lógico de los marcajes
- ✅ Tiene mejor manejo de lock files
- ✅ Es más fácil diagnosticar problemas
- ✅ Previene marcajes duplicados o incorrectos

## Fecha de Solución

9 de febrero de 2026
