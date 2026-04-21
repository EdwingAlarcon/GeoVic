# 📘 Guía de Instalación de GeoVictoria

Esta guía le ayudará a instalar y configurar GeoVictoria en cualquier PC o servidor Windows.

## 📋 Requisitos Previos

Antes de comenzar, necesita:

1. **Python 3.8 o superior**
   - Descargar desde: https://www.python.org/downloads/
   - ⚠️ **IMPORTANTE**: Durante la instalación, marque la opción **"Add Python to PATH"**

2. **Conexión a Internet**
   - Para descargar dependencias y el navegador Chromium

3. **Sus credenciales de GeoVictoria**
   - Usuario
   - Contraseña

## 🚀 Instalación Paso a Paso

### Opción 1: Instalación Automatizada (Recomendada)

1. **Descargue el proyecto**
   - Si tiene Git: `git clone https://github.com/EdwingAlarcon/GeoVic.git`
   - O descargue el ZIP desde GitHub y extráigalo

2. **Abra la carpeta del proyecto**
   ```
   cd GeoVic
   ```

3. **Ejecute el instalador**
   - Haga doble clic en `setup.bat`
   - O desde la terminal: `setup.bat`

4. **Siga las instrucciones en pantalla**
   - El instalador verificará Python
   - Creará un entorno virtual
   - Instalará todas las dependencias
   - Configurará Playwright

5. **Configure sus credenciales**
   - Abra el archivo `.env` con un editor de texto
   - Reemplace:
     ```
     GEOVICTORIA_USER=su_usuario_aqui
     GEOVICTORIA_PASSWORD=su_contraseña_aqui
     ```
   - Con sus credenciales reales:
     ```
     GEOVICTORIA_USER=juan.perez
     GEOVICTORIA_PASSWORD=MiContraseña123
     ```
   - Guarde el archivo

6. **¡Listo! Pruebe el sistema**
   ```
   scripts\ejecutar_manual.bat
   ```

### Opción 2: Instalación Manual

Si prefiere instalar manualmente:

```batch
# 1. Crear entorno virtual
python -m venv .venv

# 2. Activar entorno virtual
.venv\Scripts\activate

# 3. Actualizar pip
python -m pip install --upgrade pip

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Instalar Playwright
playwright install chromium

# 6. Copiar archivo de configuración
copy .env.example .env

# 7. Editar .env con sus credenciales
notepad .env
```

## ✅ Verificar la Instalación

Para verificar que todo está instalado correctamente:

```batch
# Activar entorno virtual
.venv\Scripts\activate

# Verificar Python
python --version

# Verificar dependencias
pip list

# Verificar credenciales
type .env
```

## 🎯 Primeros Pasos

### Prueba Manual

Ejecute un marcaje manual de prueba:

```batch
scripts\ejecutar_manual.bat
```

Esto abrirá el navegador y realizará un marcaje de prueba.

### Iniciar el Programador Automático

Para que el sistema funcione automáticamente:

```batch
scripts\iniciar_programador.bat
```

El programador se ejecutará y marcará automáticamente según los horarios configurados.

### Ver Estado del Sistema

Para verificar el estado actual:

```batch
scripts\ver_estado.bat
```

## 🔧 Configuración Avanzada

### Horarios de Marcaje

Los horarios están configurados en `src\programador.py`:

- **Lunes a Viernes:**
  - Entrada: 7:00 AM (±2-8 minutos)
  - Salida: 5:00 PM (±3-12 minutos)

- **Sábados:**
  - Entrada: 7:00 AM (±2-8 minutos)
  - Salida: 1:00 PM (±3-12 minutos)

Para modificar los horarios, edite las variables en el archivo.

### Modo Headless

Para ejecutar sin ver el navegador, edite `.env`:

```
HEADLESS=true
```

## 🐛 Solución de Problemas

### Error: "Python no está instalado"

- Instale Python desde https://www.python.org/downloads/
- Asegúrese de marcar "Add Python to PATH" durante la instalación
- Reinicie la terminal después de instalar

### Error: "No module named 'playwright'"

```batch
.venv\Scripts\activate
pip install playwright
playwright install chromium
```

### Error: "Credenciales no configuradas"

- Verifique que el archivo `.env` existe en la raíz del proyecto
- Asegúrese de que contiene sus credenciales correctas
- El archivo debe llamarse `.env` (sin .example)

### El navegador no se abre

- Verifique que Playwright está instalado: `playwright install chromium`
- Intente ejecutar con modo visible (HEADLESS=false en .env)

### Marcajes duplicados

```batch
scripts\SOLUCION_HOY.bat
```

Este script limpiará los marcajes del día actual.

## 📚 Documentación Adicional

- [README.md](README.md) - Descripción general del proyecto
- [INSTALACION_RAPIDA.md](INSTALACION_RAPIDA.md) - Guía rápida de instalación
- [docs/](docs/) - Documentación detallada

## 🆘 Soporte

Si encuentra problemas:

1. Revise la sección de solución de problemas
2. Consulte los logs en `src\logs\`
3. Abra un issue en GitHub: https://github.com/EdwingAlarcon/GeoVic/issues

## 🔒 Seguridad

- **NUNCA** comparta su archivo `.env` con nadie
- **NUNCA** suba el archivo `.env` a GitHub o repositorios públicos
- El archivo `.gitignore` ya está configurado para protegerlo

---

**¿Necesita ayuda?** Consulte el [README.md](README.md) o abra un issue en GitHub.
