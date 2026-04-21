# 📦 GeoVic - Proyecto Listo para Exportar

## ✅ Estado del Proyecto

El proyecto **GeoVic** está completamente configurado y listo para ser exportado a cualquier PC o servidor. Cualquier usuario puede instalarlo fácilmente con sus propias credenciales.

---

## 🎯 Para el Usuario Final (3 Pasos)

### 1️⃣ Obtener el Proyecto

**Opción A: Desde GitHub (Recomendado)**
```bash
git clone https://github.com/EdwingAlarcon/GeoVic.git
cd GeoVic
```

**Opción B: Archivo ZIP**
- Descargue el archivo `GeoVic-Portable.zip`
- Extraiga a una carpeta
- Abra la terminal en esa carpeta

### 2️⃣ Instalar (Automático)

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
bash setup.sh
```

El instalador hace todo automáticamente:
- ✅ Verifica Python
- ✅ Crea entorno virtual
- ✅ Instala dependencias
- ✅ Descarga navegador Chromium
- ✅ Crea archivo .env

### 3️⃣ Configurar Credenciales

Edite el archivo `.env`:
```bash
GEOVICTORIA_USER=tu_usuario
GEOVICTORIA_PASSWORD=tu_contraseña
```

### ✅ ¡Usar!

```bash
# Windows - Prueba manual
scripts\ejecutar_manual.bat

# Windows - Programador automático
scripts\iniciar_programador.bat

# Verificar instalación
scripts\verificar_instalacion.bat
```

---

## 📁 Archivos Incluidos

### 🎯 Instaladores y Guías
- ✅ `setup.bat` - Instalador automático para Windows
- ✅ `setup.sh` - Instalador automático para Linux/Mac
- ✅ `LEEME_PRIMERO.txt` - Inicio rápido
- ✅ `README.md` - Documentación principal
- ✅ `GUIA_INSTALACION.md` - Guía detallada paso a paso
- ✅ `COMO_EXPORTAR.md` - Guía de distribución del proyecto
- ✅ `PROYECTO_LISTO.md` - Este archivo

### 🔧 Scripts de Utilidad
- ✅ `scripts/ejecutar_manual.bat` - Marcaje manual
- ✅ `scripts/iniciar_programador.bat` - Programador automático
- ✅ `scripts/ver_estado.bat` - Ver estado del sistema
- ✅ `scripts/verificar_instalacion.bat` - Verificar instalación
- ✅ `scripts/ver_festivos.bat` - Listar festivos de Colombia
- ✅ `scripts/SOLUCION_HOY.bat` - Limpiar marcajes duplicados

### 📦 Exportación
- ✅ `exportar_proyecto.bat` - Crear ZIP para distribución
- ✅ `exportar_exclude.txt` - Lista de archivos a excluir

### 🔒 Seguridad
- ✅ `.env.example` - Plantilla de configuración (sin credenciales)
- ✅ `.gitignore` - Protección de archivos sensibles

### 💻 Código Fuente
- ✅ `src/geovictoria.py` - Script principal de marcaje
- ✅ `src/programador.py` - Programador automático
- ✅ `src/festivos_colombia.py` - Gestión de festivos
- ✅ `src/cache_estado.py` - Caché de estados
- ✅ `requirements.txt` - Dependencias de Python

---

## 🚀 Métodos de Distribución

### Método 1: GitHub (Recomendado)

```bash
# Ya está listo en:
https://github.com/EdwingAlarcon/GeoVic
```

**Ventajas:**
- ✅ Actualizaciones automáticas con `git pull`
- ✅ Versionado y control de cambios
- ✅ Fácil distribución

**El usuario solo hace:**
```bash
git clone https://github.com/EdwingAlarcon/GeoVic.git
cd GeoVic
setup.bat
```

### Método 2: Archivo ZIP

**Para crear el ZIP:**
```bash
exportar_proyecto.bat
```

Esto crea `GeoVic-Portable.zip` con:
- ✅ Todo el código necesario
- ✅ Scripts de instalación
- ✅ Documentación completa
- ❌ SIN credenciales
- ❌ SIN entorno virtual
- ❌ SIN logs personales

**El usuario solo hace:**
1. Extraer el ZIP
2. Ejecutar `setup.bat`
3. Configurar `.env`

### Método 3: Red Compartida

Copie toda la carpeta del proyecto a una red compartida, asegurándose de:
- ❌ NO copiar `.env`
- ❌ NO copiar `.venv/`
- ❌ NO copiar `src/logs/`

---

## 🔒 Seguridad Integrada

### Protección de Credenciales

1. **Archivo `.env` protegido**
   - Incluido en `.gitignore`
   - Nunca se sube a Git
   - Cada usuario usa el suyo

2. **Plantilla `.env.example`**
   - SIN credenciales reales
   - Solo valores de ejemplo
   - Base para que cada usuario cree su `.env`

3. **Scripts de exportación**
   - Excluyen automáticamente `.env`
   - Excluyen logs personales
   - Solo incluyen código limpio

### Verificación

```bash
# Verificar que .env está protegido
type .gitignore | findstr .env
# Debe mostrar: .env

# Verificar que .env.example no tiene credenciales
type .env.example
# Debe mostrar: su_usuario_aqui, su_contraseña_aqui
```

---

## ✅ Checklist de Exportación

Antes de distribuir, verificar:

- [x] ✅ Archivo `.env.example` con plantilla
- [x] ✅ Archivo `.env` real NO incluido
- [x] ✅ `.gitignore` configurado
- [x] ✅ `setup.bat` funcional
- [x] ✅ `setup.sh` funcional
- [x] ✅ `requirements.txt` actualizado
- [x] ✅ Documentación completa
- [x] ✅ Scripts de utilidad funcionando
- [x] ✅ Script de verificación incluido
- [x] ✅ Logs personales excluidos
- [x] ✅ Entorno virtual excluido

---

## 📊 Características del Sistema

### Funcionalidades

- ✅ **Marcaje automático** - Entrada y salida programadas
- ✅ **Horarios aleatorios** - Simula comportamiento humano
- ✅ **Festivos de Colombia** - Calendario oficial integrado
- ✅ **Logs detallados** - Registro completo de operaciones
- ✅ **Scripts de utilidad** - Verificación, diagnóstico, corrección
- ✅ **Zona horaria Colombia** - America/Bogota

### Horarios Predeterminados

**Lunes a Viernes:**
- Entrada: 7:00 AM (±2-8 minutos)
- Salida: 5:00 PM (±3-12 minutos)

**Sábados:**
- Entrada: 7:00 AM (±2-8 minutos)
- Salida: 1:00 PM (±3-12 minutos)

**Excluye:**
- Domingos
- Festivos nacionales de Colombia

---

## 🆘 Soporte al Usuario

### Documentación Incluida

1. **LEEME_PRIMERO.txt** - Guía de inicio rápido
2. **GUIA_INSTALACION.md** - Instalación paso a paso
3. **README.md** - Documentación completa
4. **COMO_EXPORTAR.md** - Distribución del proyecto

### Scripts de Diagnóstico

```bash
# Verificar instalación
scripts\verificar_instalacion.bat

# Ver estado del sistema
scripts\ver_estado.bat

# Verificar festivos
scripts\ver_festivos.bat
```

### Solución de Problemas Comunes

**Python no instalado:**
```
Descargar desde: https://www.python.org/downloads/
Marcar "Add Python to PATH" durante instalación
```

**Credenciales no configuradas:**
```
Editar archivo .env con credenciales reales
```

**Marcajes duplicados:**
```bash
scripts\SOLUCION_HOY.bat
```

---

## 🎓 Guía para Distribuidores

### Para Compartir el Proyecto

**Opción 1: URL de GitHub**
```
Envíe: https://github.com/EdwingAlarcon/GeoVic
Instrucciones: git clone + setup.bat + configurar .env
```

**Opción 2: Archivo ZIP**
```
1. Ejecute: exportar_proyecto.bat
2. Comparta: GeoVic-Portable.zip
3. Instrucciones: extraer + setup.bat + configurar .env
```

**Opción 3: Red compartida**
```
1. Copie la carpeta completa (sin .env, .venv, logs)
2. Los usuarios ejecutan setup.bat desde allí
```

### Instrucciones Simples para Usuarios

```
═══════════════════════════════════════════
INSTALACIÓN EN 3 PASOS:

1. Ejecutar:     setup.bat
2. Configurar:   Editar .env con credenciales
3. Probar:       scripts\ejecutar_manual.bat

¡Listo!
═══════════════════════════════════════════
```

---

## 📈 Actualizaciones Futuras

### Para actualizar el proyecto en GitHub:

```bash
git add .
git commit -m "Descripción de cambios"
git push origin main
```

### Para que usuarios actualicen:

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

## ✅ Resumen Final

### El proyecto está listo con:

1. ✅ **Instalador automático** (`setup.bat` / `setup.sh`)
2. ✅ **Protección de credenciales** (`.gitignore` + `.env.example`)
3. ✅ **Documentación completa** (5 guías diferentes)
4. ✅ **Scripts de utilidad** (8+ scripts listos)
5. ✅ **Sistema de verificación** (`verificar_instalacion.bat`)
6. ✅ **Exportador automático** (`exportar_proyecto.bat`)
7. ✅ **Soporte multiplataforma** (Windows, Linux, Mac)

### Cualquier usuario puede:

1. ✅ Descargar el proyecto (Git o ZIP)
2. ✅ Ejecutar un solo comando (`setup.bat`)
3. ✅ Configurar sus credenciales (editar `.env`)
4. ✅ Comenzar a usar inmediatamente

---

**🎯 El proyecto está 100% listo para distribuir y usar en cualquier PC o servidor.**

**🔗 GitHub:** https://github.com/EdwingAlarcon/GeoVic
