# GeoVictoria - Marcaje Automático de Asistencia 🇨🇴

Sistema automatizado de marcaje de asistencia para GeoVictoria, configurado específicamente para Colombia con soporte completo de festivos nacionales.

## 📋 Características

✅ **Programación automática** - Lunes a Viernes y Sábados  
✅ **Horarios aleatorios** - Simula comportamiento humano natural  
✅ **Exclusión de festivos** - Calendario oficial de Colombia  
✅ **Horarios personalizados** - Diferentes para semana y sábados  
✅ **Logs detallados** - Registro completo de operaciones  
✅ **Zona horaria Colombia** - America/Bogota  
✅ **Validación inteligente** - Omite domingos y festivos  

## ⚙️ Horarios Configurados

### 📅 Lunes a Viernes
- **Entrada:** 7:00 AM (±2 a 8 minutos de variación aleatoria)
- **Salida:** 5:00 PM (±3 a 12 minutos de variación aleatoria)

### 📅 Sábados
- **Entrada:** 7:00 AM (±2 a 8 minutos de variación aleatoria)
- **Salida:** 1:00 PM (±3 a 12 minutos de variación aleatoria)

### 🎲 Horarios Aleatorios
El sistema genera horarios aleatorios cada día para simular un comportamiento humano natural:
- **Entrada**: Puede variar de 2 minutos antes a 8 minutos después (comportamiento puntual realista)
- **Salida**: Puede variar de 3 minutos antes a 12 minutos después (tendencia a quedarse un poco más)
- Los horarios se recalculan automáticamente cada día

### ❌ Días Excluidos
- **Domingos** - No laboral
- **Festivos de Colombia** - Cálculo automático anual

## 🚀 Instalación

### 1. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 2. Instalar navegadores de Playwright

```bash
playwright install chromium
```

### 3. Configurar credenciales

Cree un archivo `.env` en el mismo directorio del script:

```env
GEOVICTORIA_USER=su_usuario
GEOVICTORIA_PASSWORD=su_contraseña
```

**⚠️ IMPORTANTE**: Nunca comparta el archivo `.env` ni lo suba a repositorios públicos.

## 📖 Uso

### Opción 1: Marcaje Manual (Una vez)

**Windows:**
```bash
scripts\ejecutar_manual.bat
```

**Linux/Mac:**
```bash
python src/geovictoria.py
```

### Opción 2: Programador Automático (Recomendado)

**Windows:**
```bash
scripts\iniciar_programador.bat
```

**Linux/Mac:**
```bash
python src/programador.py
```

El programador ejecutará automáticamente los marcajes según los horarios configurados.

### Opción 3: Ver Festivos del Año

**Windows:**
```bash
scripts\ver_festivos.bat
```

**Linux/Mac:**
```bash
python src/festivos_colombia.py
```

## 📁 Estructura del Proyecto

```
GEO/
├── src/                           # Código fuente
│   ├── __init__.py               # Módulo Python
│   ├── geovictoria.py            # Script principal de marcaje
│   ├── programador.py            # Programador con horarios automáticos
│   └── festivos_colombia.py      # Gestión de festivos colombianos
├── scripts/                       # Scripts ejecutables
│   ├── iniciar_programador.bat   # Iniciar programador (Windows)
│   ├── ejecutar_manual.bat       # Marcaje manual único (Windows)
│   └── ver_festivos.bat          # Ver festivos del año (Windows)
├── config/                        # Archivos de configuración
│   └── .env.example              # Plantilla de credenciales
├── logs/                          # Logs automáticos
├── .venv/                         # Entorno virtual Python (auto-generado)
├── .env                           # Credenciales (crear manualmente)
├── requirements.txt               # Dependencias Python
└── README.md                      # Documentación
```

## 🎯 Festivos de Colombia

El sistema incluye automáticamente:
- ✅ Festivos fijos (Año Nuevo, Independencia, Navidad, etc.)
- ✅ Festivos móviles según Ley Emiliani
- ✅ Semana Santa y festivos basados en Pascua
- ✅ Actualización automática cada año

## 📊 Logs

Los logs se guardan automáticamente en:src/programador.py](src/
```
logs/geovictoria_YYYYMMDD.log   # Marcajes individuales
logs/programador_YYYYMMDD.log   # Eventos del programador
```

## 🔧 Personalización de Horarios

Para modificar los horarios, editar en [programador.py](programador.py) la clase `HorarioConfig`:

```python
class HorarioConfig:
    # Lunes a Viernes
    ENTRADA_SEMANA_HORA = 7      # Hora de entrada (0-23)
    ENTRADA_SEMANA_MINUTO = 0    # Minuto de entrada (0-59)
    SALIDA_SEMANA_HORA = 17      # Hora de salida (5 PM)
    SALIDA_SEMANA_MINUTO = 0     # Minuto de salida
    
    # Sábados
    ENTRADA_SABADO_HORA = 7      # Hora de entrada sábado
    ENTRADA_SABADO_MINUTO = 0
    SALIDA_SABADO_HORA = 13      # Hora de salida sábado (1 PM)
    SALIDA_SABADO_MINUTO = 0
    
    # Variación aleatoria (en minutos) - Comportamiento humano realista
    VARIACION_ENTRADA_MIN = -2   # Ocasionalmente llega 2 min antes
    VARIACION_ENTRADA_MAX = 8    # o hasta 8 min tarde
    VARIACION_SALIDA_MIN = -3    # Ocasionalmente sale 3 min antes
    VARIACION_SALIDA_MAX = 12    # o hasta 12 min tarde (más común)
```

## 🖥️ Ejecución Permanente (24/7)

Para que el programador funcione siempre, configurar como servicio del sistema:

### Windows - Task Scheduler

1. Abrir "Programador de tareas"
2. Crear tarea básica:
   - Nombre: "GeoVictoria Marcajes"
   - Desencadenador: "Al iniciar el sistema"
   - Acción: Ejecutar `scripts\iniciar_programador.bat`
   - Iniciar en: Ruta completa a la carpeta GEO
   - Configurar para ejecutar aunque el usuario no haya iniciado sesión

### Linux - systemd

Crear archivo `/etc/systemd/system/geovictoria.service`:
```ini
[Unit]
Description=GeoVictoria Marcaje Automático
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/a/GEsrc/O
ExecStart=/usr/bin/python3 programador.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar:
```bash
sudo systemctl enable geovictoria
sudo systemctl start geovictoria
```

## 🐛 Solución de Problemas

### El programador no ejecuta marcajes
- ✅ Verificar que el script esté corriendo
- ✅ Revisar logs en `logs/programador_*.log`
- ✅ Confirmar credenciales en `.env`
- ✅ Verificar zona horaria del sistema

### No detecta festivos correctamente
- ✅ Ejecutar `python festivos_colombia.py` para verificar
- ✅ El cálculo es automático, no requiere mantenimiento

### Error de zona horaria
```bash
pip install pytz tzdata
```

## 📝 Ejemplo de Salida del Programador

```
================================================================================
🔔 Intento de marcaje programado: ENTRADA SEMANA (L-V)
📅 Fecha: Lunes, 23 de Enero de 2026
🕐 Hora: 07:00:00
✅ Día laborable confirmado - Ejecutando ENTRADA SEMANA (L-V)...
==============================================================
Iniciando marcaje automático GeoVictoria
Usuario: tu_usuario
==============================================================
✅ Login exitoso
✅ Iframe encontrado
✅ Marcaje de Entrada realizado
==============================================================
✅ MARCAJE EXITOSO: Entrada
Hora: 2026-01-23 07:00:15
==============================================================
✅ ENTRADA SEMANA (L-V) completado exitosamente
================================================================================
```

## ⚠️ Notas Importantes

1. **El programador debe estar corriendo** para que funcione la automatización
2. **Festivos automáticos** - No requiere actualización manual
3. **Zona horaria** - Configurada para `America/Bogota`
4. **Validación antes de marcar** - Siempre verifica si es día laborable

---

**Desarrollado para Colombia 🇨🇴**

- ✅ Semana Santa y festivos basados en Pascua
- ✅ Actualización automática cada año

## 📊 Logs

Los logs se guardan automáticamente en:
```
logs/geovictoria_YYYYMMDD.log   # Marcajes individuales
logs/programador_YYYYMMDD.log   # Eventos del programador
```

Cada ejecución registra:
- Fecha y hora exacta
- Tipo de marcaje (Entrada/Salida)
- Errores o advertencias
- Resultado final

## ⚙️ Configuración avanzada

Edite la clase `Config` en el script para ajustar:

```python
class Config:
    IFRAME_TIMEOUT = 60000      # Tiempo de espera para iframes (ms)
    BUTTON_TIMEOUT = 5000       # Tiempo de espera para botones (ms)
    MAX_RETRIES = 3             # Número de reintentos
    RETRY_DELAY = 2             # Segundos entre reintentos
    HEADLESS = False            # True para ejecutar sin interfaz gráfica
```

## 🔒 Seguridad

- ✅ Credenciales en archivo `.env` (no en el código)
- ✅ Archivo `.env` debe estar en `.gitignore`
- ✅ Conexión HTTPS al portal
- ✅ Sin almacenamiento de contraseñas en logs

## 🐛 Solución de problemas

### Error: "Credenciales no encontradas"
- Verifique que el archivo `.env` existe
- Confirme que las variables están bien escritas

### Error: "Timeout durante login"
- Verifique usuario y contraseña
- Revise su conexión a internet

### Error: "Iframe no encontrado"
- La página puede haber cambiado
- Intente aumentar `IFRAME_TIMEOUT` en Config

## 📝 Notas

- El script mantiene el navegador visible para que pueda verificar el proceso
- Se recomienda ejecutar en horarios de entrada/salida laboral
- Los logs se mantienen organizados por fecha
