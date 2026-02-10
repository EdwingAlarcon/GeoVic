# ⚡ Instalación Rápida - GeoVic

## 🎯 **Resumen de lo que necesitas:**

### **1. Python 3.8+**
📥 https://www.python.org/downloads/
⚠️ Marcar "Add Python to PATH" durante instalación

### **2. Clonar/Descargar Proyecto**
```bash
git clone https://github.com/EdwingAlarcon/GeoVic.git
cd GeoVic
```

### **3. Instalar Dependencias**
```bash
pip install -r requirements.txt
playwright install chromium
```

### **4. Crear archivo .env**
```env
GEOVICTORIA_USER=tu_usuario
GEOVICTORIA_PASSWORD=tu_contraseña
```

### **5. Probar**
```bash
# Windows
.\scripts\ejecutar_manual.bat

# Linux/Mac
python src/geovictoria.py
```

### **6. Iniciar Programador**
```bash
# Windows
.\scripts\iniciar_programador.bat

# Linux/Mac
python src/programador.py
```

---

## 📦 **Paquetes que se instalan:**

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `playwright` | ≥1.48.0 | Automatización del navegador |
| `python-dotenv` | ≥1.0.0 | Manejo de variables de entorno (.env) |
| `apscheduler` | ≥3.10.4 | Programación de tareas automáticas |

**Tamaño total aproximado:** ~150 MB (incluye Chromium)

---

## 🖥️ **Requisitos Mínimos del PC:**

- ✅ 4 GB RAM (8 GB recomendado)
- ✅ 500 MB espacio en disco
- ✅ Windows 10/11, Linux, o macOS
- ✅ Conexión a Internet

---

## ✅ **Verificación Rápida:**

```bash
# ¿Python instalado?
python --version

# ¿Playwright instalado?
playwright --version

# ¿Dependencias instaladas?
pip list | findstr playwright

# ¿Archivo .env existe?
# Windows: dir .env
# Linux/Mac: ls -la .env
```

---

## 📚 **Para más detalles:**
Ver: **INSTALACION.md**
