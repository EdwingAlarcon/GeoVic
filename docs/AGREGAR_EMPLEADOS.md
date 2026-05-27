# Gestión de Empleados — GeoVic

Esta guía explica cómo agregar, modificar o desactivar empleados en el sistema de marcaje automático.

---

## Índice

1. [¿Cómo funciona la configuración de empleados?](#cómo-funciona)
2. [Crear el archivo employees.json](#crear-employeesjson)
3. [Estructura del archivo explicada campo a campo](#estructura)
4. [Agregar un nuevo empleado](#agregar-un-nuevo-empleado)
5. [Desactivar un empleado temporalmente](#desactivar-un-empleado)
6. [Aplicar los cambios (reiniciar el programador)](#aplicar-los-cambios)
7. [Casos especiales de horario](#casos-especiales-de-horario)
8. [Solución de problemas](#solución-de-problemas)

---

## ¿Cómo funciona?

El sistema lee la lista de empleados desde `config/employees.json` **cada vez que arranca el programador**. Cada empleado tiene:

- Sus propias credenciales de GeoVictoria
- Su propio horario de entrada y salida
- Su propio archivo de registro (`src/logs/registro_{id}.json`)

Esto significa que **agregar o quitar empleados nunca afecta el historial de los demás**: los archivos de registro son independientes por empleado.

---

## Crear employees.json

El archivo `config/employees.json` **no está incluido en el repositorio** (está en `.gitignore` para proteger las contraseñas). Debes crearlo manualmente copiando el ejemplo:

```
config/
├── employees.example.json   ← plantilla (incluida en el repo)
└── employees.json           ← tu archivo real (debes crearlo, NO subir a Git)
```

**Pasos:**

1. Abre la carpeta `config/`
2. Copia `employees.example.json`
3. Renombra la copia a `employees.json`
4. Edítala con un editor de texto (Notepad, VS Code, etc.)
5. Reemplaza los datos de ejemplo con las credenciales reales

---

## Estructura

```jsonc
{
  "employees": [
    {
      "id": "emp1",                     // Identificador único interno (no cambiar una vez creado)
      "nombre": "Nombre Completo",       // Nombre para los logs (solo informativo)
      "usuario": "usuario_geovictoria",  // Usuario con el que entra al portal
      "password": "contraseña_real",     // Contraseña del portal
      "activo": true,                    // false = desactivado (no se marca, no se borra)
      "horario": {
        "entrada_semana_hora": 7,        // Hora de entrada lunes-viernes (formato 24h)
        "entrada_semana_minuto": 0,      // Minuto de entrada
        "salida_semana_hora": 17,        // Hora de salida lunes-viernes (17 = 5:00 PM)
        "salida_semana_minuto": 0,
        "entrada_sabado_hora": 7,        // Hora de entrada sábado
        "entrada_sabado_minuto": 0,
        "salida_sabado_hora": 13,        // Hora de salida sábado (13 = 1:00 PM)
        "salida_sabado_minuto": 0,
        "trabaja_sabados": true          // false = el empleado NO trabaja sábados
      }
    }
  ]
}
```

### Notas sobre el campo `id`

- Debe ser **único** en el archivo. Convencionalmente: `emp1`, `emp2`, `emp3`…
- **No lo cambies** una vez que el empleado tiene historial. El archivo de registro está vinculado al id (`registro_emp1.json`). Si cambias el id, el programador lo tratará como empleado nuevo y perderá el historial.
- Puede ser cualquier texto sin espacios: `emp4`, `juridico`, `temporal_junio`, etc.

---

## Agregar un nuevo empleado

### Paso 1 — Edita `config/employees.json`

Abre el archivo y agrega un nuevo objeto al array `"employees"`. Asegúrate de:

- Usar una coma `,` después del bloque anterior
- Usar un `id` que no exista todavía
- Que el JSON esté bien formateado (sin comas finales, corchetes cerrados, etc.)

**Ejemplo con 3 empleados existentes y uno nuevo (emp4):**

```json
{
  "employees": [
    {
      "id": "emp1",
      "nombre": "Sergio Giraldo",
      "usuario": "sgiraldo",
      "password": "password123",
      "activo": true,
      "horario": {
        "entrada_semana_hora": 7,
        "entrada_semana_minuto": 0,
        "salida_semana_hora": 17,
        "salida_semana_minuto": 0,
        "entrada_sabado_hora": 7,
        "entrada_sabado_minuto": 0,
        "salida_sabado_hora": 13,
        "salida_sabado_minuto": 0,
        "trabaja_sabados": true
      }
    },
    {
      "id": "emp2",
      "nombre": "Gonzalo Avila",
      "usuario": "gavila",
      "password": "password456",
      "activo": true,
      "horario": {
        "entrada_semana_hora": 7,
        "entrada_semana_minuto": 0,
        "salida_semana_hora": 18,
        "salida_semana_minuto": 0,
        "entrada_sabado_hora": 7,
        "entrada_sabado_minuto": 0,
        "salida_sabado_hora": 13,
        "salida_sabado_minuto": 0,
        "trabaja_sabados": true
      }
    },
    {
      "id": "emp4",
      "nombre": "Ana Martínez",
      "usuario": "amartinez",
      "password": "password789",
      "activo": true,
      "horario": {
        "entrada_semana_hora": 8,
        "entrada_semana_minuto": 0,
        "salida_semana_hora": 17,
        "salida_semana_minuto": 30,
        "entrada_sabado_hora": 8,
        "entrada_sabado_minuto": 0,
        "salida_sabado_hora": 13,
        "salida_sabado_minuto": 0,
        "trabaja_sabados": false
      }
    }
  ]
}
```

> **Truco para verificar que el JSON es válido:** pega el contenido en [jsonlint.com](https://jsonlint.com) antes de guardar.

### Paso 2 — Reinicia el programador

Ver sección [Aplicar los cambios](#aplicar-los-cambios) más abajo.

### Paso 3 — Verifica en el log

Al arrancar, el programador lista los empleados activos. Confirma que el nuevo aparece:

```
👥 Empleados activos: 4
  • [emp1] Sergio Giraldo  — L-V 07:00/17:00
  • [emp2] Gonzalo Avila   — L-V 07:00/18:00
  • [emp4] Ana Martínez    — L-V 08:00/17:30
```

El log está en: `src/logs/programador_YYYYMMDD.log`

---

## Desactivar un empleado

Si un empleado sale de la empresa o toma una licencia larga, no lo borres del archivo. Cambia `"activo": false`:

```json
{
  "id": "emp2",
  "nombre": "Gonzalo Avila",
  "activo": false,
  ...
}
```

El programador lo ignorará completamente. Para reactivarlo cuando regrese, vuelve a poner `"activo": true` y reinicia el programador.

---

## Aplicar los cambios

El programador **no recarga el archivo en caliente**: necesitas reiniciarlo para que lea los cambios.

### Opción A — Reinicio rápido (recomendado)

Ejecuta:
```
scripts\reiniciar_programador.bat
```

Este script se encarga de todo: detiene la instancia actual, limpia el lock file y abre una nueva ventana con el programador actualizado.

### Opción B — Reinicio manual

1. Cierra la ventana del programador (o presiona `Ctrl+C` en ella)
2. Borra el lock file si quedó: `src/logs/programador.lock`
3. Ejecuta: `scripts\iniciar_programador_vigilado.bat` (o `iniciar_programador.bat`)

> **¿Y los marcajes de hoy de los empleados existentes?**  
> No se pierden. Al arrancar, el programador verifica el estado de cada empleado en el portal y sincroniza su registro local. Si ya marcaron entrada, lo detecta y no lo marca de nuevo.

---

## Casos especiales de horario

### Empleado que no trabaja sábados

```json
"trabaja_sabados": false
```

Los campos `entrada_sabado_*` y `salida_sabado_*` pueden dejarse con cualquier valor; serán ignorados.

### Empleado que entra a la mitad de hora

```json
"entrada_semana_hora": 7,
"entrada_semana_minuto": 30
```

### Empleado con horario diferente para sábado

```json
"entrada_semana_hora": 7,
"entrada_semana_minuto": 0,
"salida_semana_hora": 17,
"salida_semana_minuto": 0,
"entrada_sabado_hora": 8,
"entrada_sabado_minuto": 0,
"salida_sabado_hora": 12,
"salida_sabado_minuto": 0,
"trabaja_sabados": true
```

### Ventana de tolerancia

El programador ejecuta el marcaje si la hora actual está dentro de **±30 minutos** de la hora programada. Si el PC estuvo apagado y arranca tarde, el job de verificación horaria (se ejecuta cada hora en punto) intenta recuperar marcajes pendientes hasta las 12:00 para entradas y hasta las 23:00 para salidas.

---

## Solución de problemas

### El nuevo empleado no aparece en el log

- Verifica que el JSON es válido (sin errores de sintaxis)
- Confirma que `"activo": true` está en el bloque del empleado
- Asegúrate de que reiniciaste el programador **después** de guardar el archivo

### Error "campo faltante o vacío"

Todos estos campos son obligatorios: `id`, `nombre`, `usuario`, `password`. Si alguno está vacío o falta, el programador rechaza ese empleado al inicio.

### El nuevo empleado ya marcó entrada hoy manualmente

No hay problema. Al arrancar, el programador hace una verificación de pendientes: si detecta que el botón del portal ya es "Salida" (entrada ya hecha), sincroniza el registro local y no vuelve a marcar. Solo marcará la salida a la hora configurada.

### Necesito marcar salida ahora para el empleado nuevo

Usa el script de marcaje forzado:

```bash
# Salida para un empleado específico
python scripts/marcar_forzado.py salida emp4

# Salida para todos los empleados activos
python scripts/marcar_forzado.py salida
```

### El programador marca dos veces al mismo empleado

Revisa que no haya dos entradas con el mismo `id` en el JSON. Cada id debe ser único.

---

## Archivos relacionados

| Archivo | Descripción |
|---------|-------------|
| `config/employees.json` | Configuración de empleados (tú lo creas, no está en Git) |
| `config/employees.example.json` | Plantilla de referencia (incluida en el repo) |
| `src/empleados.py` | Módulo que carga y valida el JSON |
| `src/logs/registro_{id}.json` | Historial de marcajes por empleado |
| `scripts/reiniciar_programador.bat` | Reinicia el programador para aplicar cambios |
| `scripts/marcar_forzado.py` | Marcaje manual de emergencia, bypasa ventana de tiempo |
