# 📦 Guía de Exportación del Proyecto GeoVictoria

Esta guía explica cómo exportar el proyecto GeoVictoria para instalarlo en otro PC o servidor.

## 🎯 Objetivo

Permitir que cualquier usuario pueda:
1. Descargar/copiar el proyecto
2. Ejecutar un instalador
3. Configurar sus credenciales
4. Comenzar a usar el sistema

## 📁 Archivos Necesarios para Exportar

### ✅ Archivos que DEBE incluir:

```
GeoVic/
├── src/                          # Código fuente
│   ├── __init__.py
│   ├── geovictoria.py
│   ├── programador.py
│   ├── festivos_colombia.py
│   └── cache_estado.py
├── scripts/                      # Scripts de utilidad
│   ├── ejecutar_manual.bat
│   ├── iniciar_programador.bat
│   ├── ver_estado.bat
│   ├── verificar_instalacion.bat
│   └── ...otros scripts...
├── config/                       # Configuración (opcional)
├── docs/                         # Documentación
├── requirements.txt              # Dependencias de Python
├── .env.example                  # Plantilla de configuración
├── .gitignore                    # Protección de archivos sensibles
├── setup.bat                     # Instalador para Windows
├── setup.sh                      # Instalador para Linux/Mac
├── README.md                     # Documentación principal
├── GUIA_INSTALACION.md          # Guía detallada
└── LEEME_PRIMERO.txt            # Inicio rápido
```

### ❌ Archivos que NO DEBE incluir:

```
.env                              # ⚠️ Contiene credenciales
.venv/                            # Entorno virtual (se crea en instalación)
src/logs/                         # Logs personales
__pycache__/                      # Archivos compilados
*.pyc                             # Archivos compilados
.playwright/                      # Caché de navegadores
```

## 📤 Métodos de Exportación

### Opción 1: Repositorio Git (Recomendado)

Si usa Git y GitHub:

```bash
# 1. Asegurarse de que .gitignore está configurado
git add .gitignore

# 2. Subir todos los archivos necesarios
git add .
git commit -m "Proyecto listo para exportar"
git push origin main

# 3. El usuario final puede clonar:
git clone https://github.com/EdwingAlarcon/GeoVic.git
```

**Ventajas:**
- ✅ Versionado automático
- ✅ Fácil distribución
- ✅ Actualizaciones sencillas
- ✅ El .gitignore protege credenciales automáticamente

### Opción 2: Archivo ZIP

Si prefiere un archivo ZIP:

**Windows (PowerShell):**
```powershell
# Crear ZIP excluyendo archivos innecesarios
$exclude = @('.env', '.venv', 'src\logs', '__pycache__', '.git')
$files = Get-ChildItem -Recurse | Where-Object { 
    $file = $_
    -not ($exclude | Where-Object { $file.FullName -like "*$_*" })
}
Compress-Archive -Path $files -DestinationPath GeoVic-Portable.zip
```

**Linux/Mac:**
```bash
# Crear tar.gz excluyendo archivos innecesarios
tar -czf GeoVic-Portable.tar.gz \
    --exclude='.env' \
    --exclude='.venv' \
    --exclude='src/logs' \
    --exclude='__pycache__' \
    --exclude='.git' \
    .
```

### Opción 3: Carpeta en Red Compartida

Para distribución en red local:

1. Copie toda la carpeta del proyecto
2. Asegúrese de NO copiar:
   - `.env` (credenciales)
   - `.venv/` (entorno virtual)
   - `src/logs/` (logs personales)
3. Los usuarios pueden acceder desde la red

## 🚀 Instrucciones para el Usuario Final

Incluya estas instrucciones simples:

```
═══════════════════════════════════════════════════════════════
INSTALACIÓN EN 3 PASOS:

1. Ejecutar:     setup.bat (Windows) o bash setup.sh (Linux/Mac)
2. Configurar:   Editar archivo .env con sus credenciales
3. Usar:         scripts\ejecutar_manual.bat para probar

¡Listo! Consulte LEEME_PRIMERO.txt para más detalles.
═══════════════════════════════════════════════════════════════
```

## 📋 Checklist de Exportación

Antes de distribuir el proyecto, verifique:

- [ ] El archivo `.env.example` existe y tiene las variables correctas
- [ ] El archivo `.env` real NO está incluido
- [ ] El `.gitignore` está configurado correctamente
- [ ] Los scripts `setup.bat` y `setup.sh` funcionan
- [ ] El archivo `requirements.txt` está actualizado
- [ ] El `README.md` tiene instrucciones claras
- [ ] La carpeta `.venv` NO está incluida
- [ ] Los logs personales NO están incluidos
- [ ] El proyecto funciona en una instalación limpia

## 🧪 Prueba de Instalación

Antes de distribuir, pruebe en una máquina limpia:

1. **Copie el proyecto** a un nuevo directorio
2. **Elimine** `.venv/`, `.env`, y `src/logs/`
3. **Ejecute** `setup.bat` o `bash setup.sh`
4. **Configure** `.env` con credenciales de prueba
5. **Pruebe** que funciona: `scripts\ejecutar_manual.bat`

Si funciona correctamente, está listo para distribuir.

## 🔄 Actualización del Proyecto

Para que los usuarios actualicen a nuevas versiones:

### Con Git:
```bash
cd GeoVic
git pull origin main
pip install -r requirements.txt --upgrade
```

### Con ZIP:
1. Hacer respaldo del archivo `.env`
2. Extraer nuevo ZIP
3. Restaurar el archivo `.env`
4. Ejecutar `setup.bat` para actualizar dependencias

## 📞 Soporte al Usuario Final

Incluya estas instrucciones de soporte:

```
Si tiene problemas:

1. Ejecute: scripts\verificar_instalacion.bat
2. Revise: GUIA_INSTALACION.md
3. Consulte logs en: src\logs\
4. Abra un issue en: https://github.com/EdwingAlarcon/GeoVic/issues
```

## 🔒 Seguridad

**IMPORTANTE: Nunca incluya en la distribución:**
- ❌ Archivo `.env` con credenciales reales
- ❌ Logs con información sensible
- ❌ Tokens o claves de API
- ❌ Información personal

El `.gitignore` ya está configurado para proteger estos archivos.

## 📊 Tamaño del Proyecto

Tamaño aproximado para distribución:

- **Código fuente**: ~500 KB
- **ZIP completo**: ~1-2 MB
- **Con instalación completa** (incluye navegador): ~150-200 MB

## ✅ Resultado Final

El usuario final recibirá:
1. ✅ Código limpio sin configuración personal
2. ✅ Instalador automático funcional
3. ✅ Documentación completa y clara
4. ✅ Sistema de protección de credenciales
5. ✅ Scripts de utilidad listos para usar

---

**¿Listo para exportar?** Use el método de Git (recomendado) o cree un ZIP siguiendo esta guía.
