# 🚀 Guía Rápida - Corrección de Marcajes Duplicados

## 📋 Opción 1: Corrección Automática (Recomendado)

Ejecuta **UN SOLO** archivo para corregir todo automáticamente:

### Desde el Explorador de Windows:
1. Abre la carpeta `scripts` en el explorador de archivos
2. Haz **doble clic** en: `corregir_problema_completo.bat`
3. Sigue las instrucciones en pantalla

Este script ejecutará automáticamente:
- ✅ Instalación de dependencias
- ✅ Detener todas las instancias
- ✅ Limpiar registro corrupto
- ✅ Diagnóstico del sistema

---

## 📋 Opción 2: Paso a Paso Manual

Si prefieres ejecutar cada paso manualmente, haz doble clic en cada archivo en orden:

### 1. Instalar dependencias
📄 `instalar_psutil.bat`

### 2. Detener instancias duplicadas
📄 `detener_todas_instancias.bat`

### 3. Limpiar registro de hoy
📄 `limpiar_registro_hoy.bat`

### 4. Diagnóstico del sistema
📄 `diagnostico_sistema.bat`

### 5. Iniciar el programador
📄 `iniciar_programador.bat`

---

## 🔍 Verificar Estado

Después de la corrección, verifica que todo esté OK:

📄 `ver_estado.bat` - Estado general

---

## 📁 Ubicación de los Scripts

Todos los scripts están en la carpeta:
```
GeoVic/scripts/
```

Para abrirla desde Visual Studio Code:
1. Haz clic derecho en cualquier archivo
2. Selecciona **"Revelar en el Explorador de archivos"**
3. Navega a la carpeta `scripts`

---

## ❓ Si los Scripts No Funcionan

### Windows no permite ejecutar .bat
1. Haz clic derecho en el archivo
2. Selecciona "Propiedades"
3. Haz clic en "Desbloquear"
4. Haz clic en "Aceptar"

### Aparece "No se reconoce python"
Ejecuta primero: `instalar_dependencias.bat`

---

## 📞 Scripts Disponibles

| Script | Descripción |
|--------|-------------|
| `corregir_problema_completo.bat` | ⭐ Corrección automática completa |
| `instalar_dependencias.bat` | Instala todas las dependencias |
| `instalar_psutil.bat` | Instala solo psutil |
| `detener_todas_instancias.bat` | Detiene todos los programadores |
| `limpiar_registro_hoy.bat` | Limpia registro corrupto |
| `diagnostico_sistema.bat` | Diagnóstico completo |
| `iniciar_programador.bat` | Inicia el programador |
| `ver_estado.bat` | Ver estado general |

---

**💡 Recomendación**: Usa `corregir_problema_completo.bat` para mayor facilidad.
