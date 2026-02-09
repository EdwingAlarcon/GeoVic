# 📦 Guía de Instalación Completa - GeoVic

Guía paso a paso para instalar y configurar GeoVic en un PC nuevo.

---

## 📋 **Requisitos del Sistema**

### 1️⃣ **Sistema Operativo**
- ✅ Windows 10/11 (64 bits)
- ✅ Linux (Ubuntu 20.04+, Debian, etc.)
- ✅ macOS 11+

### 2️⃣ **Requisitos de Hardware Mínimos**
- 🖥️ 4 GB RAM (8 GB recomendado)
- 💾 500 MB de espacio en disco
- 🌐 Conexión a Internet estable

---

## 🔧 **Software Necesario**

### 1️⃣ **Python 3.8 o superior**

#### **Windows:**
1. Descargar desde: https://www.python.org/downloads/
2. Durante la instalación:
   - ✅ **Marcar**: "Add Python to PATH"
   - ✅ **Marcar**: "Install for all users" (opcional)
3. Verificar instalación:
   ```powershell
   python --version
   ```
   Debe mostrar: `Python 3.x.x`

#### **Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip
python3 --version
```

#### **macOS:**
```bash
# Usando Homebrew
brew install python3
python3 --version
```

### 2️⃣ **Git** (Opcional, para clonar el repositorio)

#### **Windows:**
Descargar desde: https://git-scm.com/download/win

#### **Linux:**
```bash
sudo apt install git
```

#### **macOS:**
```bash
brew install git
```

---

## 📥 **Instalación del Proyecto**

### **Método 1: Usando Git (Recomendado)**

```bash
# 1. Clonar el repositorio
git clone https://github.com/EdwingAlarcon/GeoVic.git

# 2. Entrar al directorio
cd GeoVic
```

### **Método 2: Descarga Manual**

1. Ir a: https://github.com/EdwingAlarcon/GeoVic
2. Clic en **Code** → **Download ZIP**
3. Descomprimir en una carpeta de tu elección
4. Abrir terminal/CMD en esa carpeta

---

## 🔌 **Instalación de Dependencias**

### 1️⃣ **Instalar librerías Python**

```bash
# Windows PowerShell o Linux/Mac Terminal
pip install -r requirements.txt
```

**Paquetes que se instalan:**
- `playwright>=1.48.0` - Para automatización del navegador
- `python-dotenv>=1.0.0` - Para manejo de variables de entorno
- `apscheduler>=3.10.4` - Para programación de tareas

### 2️⃣ **Instalar navegador Chromium**

```bash
playwright install chromium
```

Esto descarga e instala Chromium (~100 MB). Espera a que termine.

### 3️⃣ **Verificar instalación**

```bash
# Verificar que playwright esté instalado
playwright --version
```

---

## 🔑 **Configuración de Credenciales**

### **Crear archivo `.env`**

1. En la carpeta raíz del proyecto, crear un archivo llamado `.env`
2. Agregar las siguientes líneas:

```env
GEOVICTORIA_USER=tu_usuario_aqui
GEOVICTORIA_PASSWORD=tu_contraseña_aqui
```

**Ejemplo:**
```env
GEOVICTORIA_USER=juan.perez@empresa.com
GEOVICTORIA_PASSWORD=MiPassword123
```

### **⚠️ IMPORTANTE - Seguridad:**
- ❌ **NUNCA** compartas este archivo
- ❌ **NUNCA** lo subas a GitHub u otros repositorios
- ✅ El archivo `.gitignore` ya está configurado para ignorarlo

---

## ✅ **Verificación de la Instalación**

### **Prueba Manual:**

#### **Windows:**
```powershell
# Desde la carpeta del proyecto
.\scripts\ejecutar_manual.bat
```

#### **Linux/Mac:**
```bash
python src/geovictoria.py
```

Si todo está bien, deberías ver:
- ✅ Abrirse el navegador Chromium
- ✅ Login automático en GeoVictoria
- ✅ Marcaje completado exitosamente

---

## 🚀 **Iniciar el Programador Automático**

### **Windows:**

**Opción 1: Doble clic**
- Ejecutar: `scripts\iniciar_programador.bat`

**Opción 2: Desde PowerShell**
```powershell
.\scripts\iniciar_programador.bat
```

### **Linux/Mac:**
```bash
python src/programador.py
```

### **Salida esperada:**
```
================================================================================
🚀 INICIANDO PROGRAMADOR DE MARCAJES GEOVICTORIA
📍 Configurado para Colombia (incluye manejo de festivos)
================================================================================

📅 Festivos en Colombia 2026:
...

🎲 CALCULANDO HORARIOS ALEATORIOS PARA HOY:
...

📋 TRABAJOS PROGRAMADOS:
  ✓ Entrada L-V 07:01         | Próxima ejecución: 2026-02-05 07:01:00
  ✓ Salida L-V 16:59          | Próxima ejecución: 2026-02-04 16:59:00
...

⏰ Programador activo. Presione Ctrl+C para detener.
```

---

## 📊 **Verificar Estado de Ejecuciones**

### **Opción 1: Script de Verificación Detallado**

#### **Windows:**
```powershell
.\scripts\ver_estado_detallado.bat
```

#### **Linux/Mac:**
```bash
python scripts/verificar_estado.py
```

### **Opción 2: Ver Archivos de Log**
- **Registro de ejecuciones**: `src/logs/registro_ejecuciones.json`
- **Log del programador**: `src/logs/programador_YYYYMMDD.log`
- **Log de marcajes**: `src/logs/geovictoria_YYYYMMDD.log`

---

## 🔄 **Configurar Inicio Automático (Opcional)**

### **Windows - Tarea Programada:**

1. Abrir **Administrador de Tareas** (Task Scheduler)
2. Crear Tarea Básica:
   - **Nombre**: GeoVic Programador
   - **Desencadenador**: Al iniciar sesión
   - **Acción**: Iniciar un programa
   - **Programa**: `C:\ruta\completa\a\scripts\iniciar_programador.bat`

### **Linux - Systemd Service:**

1. Crear archivo de servicio:
```bash
sudo nano /etc/systemd/system/geovic.service
```

2. Contenido:
```ini
[Unit]
Description=GeoVic Marcaje Automático
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/completa/a/GeoVic
ExecStart=/usr/bin/python3 src/programador.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Activar servicio:
```bash
sudo systemctl enable geovic.service
sudo systemctl start geovic.service
```

### **macOS - LaunchAgent:**

1. Crear archivo:
```bash
nano ~/Library/LaunchAgents/com.geovic.programador.plist
```

2. Contenido:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.geovic.programador</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/ruta/completa/a/GeoVic/src/programador.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

3. Cargar:
```bash
launchctl load ~/Library/LaunchAgents/com.geovic.programador.plist
```

---

## ❓ **Solución de Problemas**

### **Error: "python: command not found"**
✅ Python no está instalado o no está en el PATH
- Reinstalar Python marcando "Add to PATH"

### **Error: "playwright: command not found"**
✅ Playwright no instalado correctamente
```bash
pip install playwright
playwright install chromium
```

### **Error: "ModuleNotFoundError: No module named 'playwright'"**
✅ Dependencias no instaladas
```bash
pip install -r requirements.txt
```

### **Error: "Credenciales no encontradas"**
✅ Archivo `.env` no existe o tiene formato incorrecto
- Verificar que el archivo se llame exactamente `.env` (con punto al inicio)
- Verificar que tenga las variables GEOVICTORIA_USER y GEOVICTORIA_PASSWORD

### **El programador no ejecuta los marcajes**
✅ Verificar que:
- El programador esté corriendo (no cerrar la ventana)
- No sea domingo o festivo
- Revisar logs en `src/logs/`

---

## 📞 **Soporte**

Si tienes problemas:
1. Revisa los logs en `src/logs/`
2. Ejecuta el verificador de estado: `scripts\ver_estado_detallado.bat`
3. Verifica que todas las dependencias estén instaladas

---

## 📝 **Lista de Verificación Post-Instalación**

- [ ] Python 3.8+ instalado y en PATH
- [ ] Git instalado (opcional)
- [ ] Proyecto descargado/clonado
- [ ] Dependencias Python instaladas (`pip install -r requirements.txt`)
- [ ] Chromium instalado (`playwright install chromium`)
- [ ] Archivo `.env` creado con credenciales
- [ ] Prueba manual exitosa
- [ ] Programador iniciado correctamente
- [ ] Inicio automático configurado (opcional)

---

✅ **¡Instalación Completada!**

El sistema ahora debería estar funcionando automáticamente. Los marcajes se realizarán según los horarios configurados.
