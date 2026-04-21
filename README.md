# GeoVictoria - Marcaje Automático de Asistencia 🇨🇴

Sistema automatizado de marcaje de asistencia para GeoVictoria, configurado específicamente para Colombia con soporte completo de festivos nacionales.

## � Instalación Rápida

### 1️⃣ Requisitos
- Python 3.8+ ([Descargar](https://www.python.org/downloads/))
- Git (opcional)

### 2️⃣ Instalación
```bash
# Clonar el repositorio
git clone https://github.com/EdwingAlarcon/GeoVic.git
cd GeoVic

# Instalar dependencias
pip install -r requirements.txt
playwright install chromium

# Configurar credenciales
# Crear archivo .env con:
# GEOVICTORIA_USER=tu_usuario
# GEOVICTORIA_PASSWORD=tu_contraseña
```

### 3️⃣ Primeros Pasos
```bash
# Windows - Marcaje manual de prueba
scripts\ejecutar_manual.bat

# Windows - Iniciar programador automático
scripts\iniciar_programador.bat
```

📖 **Guía completa:** Ver [docs/INSTALACION_COMPLETA.md](docs/INSTALACION_COMPLETA.md)

---

## �📋 Características

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

---

## 📖 Uso

### Marcaje Manual (Una Vez)

**Windows:**
```bash
scripts\ejecutar_manual.bat
```

**Linux/Mac:**
```bash
python src/geovictoria.py
```

### Programador Automático (Recomendado)

**Windows:**
```bash
scripts\iniciar_programador.bat
```

**Linux/Mac:**
```bash
python src/programador.py
```

El programador ejecutará automáticamente los marcajes según los horarios configurados.

### Ver Festivos del Año

**Windows:**
```bash
scripts\ver_festivos.bat
```

**Linux/Mac:**
```bash
python src/festivos_colombia.py
```

### Verificar Instalación

Para verificar que todo está instalado correctamente:

```bash
scripts\verificar_instalacion.bat
```

---

## 🛠️ Scripts Disponibles

El proyecto incluye varios scripts de utilidad en la carpeta `scripts/`:

| Script | Descripción |
|--------|-------------|
| `ejecutar_manual.bat` | Ejecuta un marcaje manual de prueba |
| `iniciar_programador.bat` | Inicia el programador automático |
| `ver_estado.bat` | Muestra el estado actual del sistema |
| `verificar_instalacion.bat` | Verifica que todo está instalado correctamente |
| `ver_festivos.bat` | Lista los festivos de Colombia |
| `SOLUCION_HOY.bat` | Limpia marcajes duplicados del día actual |

---

## 📦 Exportar a Otro PC

Para instalar este proyecto en otro PC o servidor:

1. **Descargue** el proyecto (Git clone o ZIP)
2. **Ejecute** `setup.bat` (Windows) o `bash setup.sh` (Linux/Mac)
3. **Configure** el archivo `.env` con las credenciales del usuario
4. **Listo** para usar

📖 Ver [COMO_EXPORTAR.md](COMO_EXPORTAR.md) para guía completa de distribución

---

## 🔒 Seguridad y Credenciales

- ✅ Cada usuario debe configurar sus propias credenciales en el archivo `.env`
- ✅ El archivo `.env` está protegido por `.gitignore` (no se sube a Git)
- ⚠️ **NUNCA** comparta su archivo `.env` con credenciales reales
- ⚠️ Use el archivo `.env.example` como plantilla (sin credenciales)

**Windows:**
```bash
scripts\ver_festivos.bat
```

**Linux/Mac:**
```bash
python src/festivos_colombia.py
```

---

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

### Problemas con marcajes duplicados
- Ver: [docs/SOLUCION_MARCAJES_DUPLICADOS.md](docs/SOLUCION_MARCAJES_DUPLICADOS.md)
- Ejecutar: `scripts\corregir_problema_completo.bat`

### Configurar tarea programada en Windows
- Ver: [docs/CONFIGURAR_TAREA_WINDOWS.md](docs/CONFIGURAR_TAREA_WINDOWS.md)
- Ejecutar: `scripts\configurar_tarea_windows.ps1`

---

## 📚 Documentación

### 🚀 Instalación y Configuración
- 📖 [Guía de Instalación](docs/GUIA_INSTALACION.md) - Guía completa paso a paso
- 📖 [Instalación Completa](docs/INSTALACION_COMPLETA.md) - Instalación detallada con opciones
- 📖 [Instalación Rápida](docs/INSTALACION_RAPIDA.md) - Instalación express en minutos
- 📖 [Configurar Tarea Windows](docs/CONFIGURAR_TAREA_WINDOWS.md) - Automatización en Windows

### 📦 Distribución y Exportación
- 📖 [Cómo Exportar](docs/COMO_EXPORTAR.md) - Exportar el proyecto a otro PC
- 📖 [Proyecto Listo](docs/PROYECTO_LISTO.md) - Estado del proyecto completo

### 🐛 Solución de Problemas
- 📖 [Marcajes Duplicados](docs/SOLUCION_MARCAJES_DUPLICADOS.md) - Resolver marcajes duplicados
- 📖 [Marcajes Múltiples](docs/SOLUCION_MARCAJES_MULTIPLES.md) - Solucionar marcajes múltiples
- 📖 [Salidas Accidentales](docs/SOLUCION_SALIDAS_ACCIDENTALES.md) - Corregir salidas accidentales

### 📂 Índice Completo
- 📖 [Ver toda la documentación](docs/README.md) - Índice completo de documentos
- 📖 [Scripts Disponibles](scripts/README.md) - Lista completa de scripts

---

**Desarrollado para Colombia 🇨🇴**

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
