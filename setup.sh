#!/bin/bash

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║          🚀 INSTALADOR DE GEOVICTORIA                          ║"
echo "║          Sistema de Marcaje Automático                        ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# PASO 0: VERIFICAR REQUISITOS PREVIOS
# ============================================================================
echo -e "${CYAN}[0/8] 🔍 Verificando requisitos del sistema...${NC}"
echo ""

# Verificar Python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR CRÍTICO: Python3 no está instalado${NC}"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${YELLOW}💡 SOLUCIÓN:${NC}"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "Ubuntu/Debian:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install python3 python3-pip python3-venv"
    echo ""
    echo "Fedora/RHEL:"
    echo "  sudo dnf install python3 python3-pip"
    echo ""
    echo "macOS:"
    echo "  brew install python3"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    exit 1
fi

# Obtener versión de Python
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}   ✅ Python $PYTHON_VERSION detectado${NC}"

# Verificar versión mínima (3.8+)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${YELLOW}   ⚠️  ADVERTENCIA: Se recomienda Python 3.8 o superior${NC}"
    echo -e "${YELLOW}   ℹ️  Tiene: $PYTHON_VERSION${NC}"
    echo -e "${YELLOW}   ℹ️  Continuando de todos modos...${NC}"
    sleep 2
fi
echo ""

# ============================================================================
# PASO 1: VERIFICAR PIP
# ============================================================================
echo -e "${CYAN}[1/8] 🔍 Verificando pip (gestor de paquetes)...${NC}"

if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    echo -e "${RED}❌ ERROR: pip no está disponible${NC}"
    echo ""
    echo -e "${YELLOW}💡 SOLUCIÓN:${NC}"
    echo "  Ubuntu/Debian: sudo apt-get install python3-pip"
    echo "  Fedora/RHEL:   sudo dnf install python3-pip"
    echo "  macOS:         pip ya debería estar instalado con Python"
    echo ""
    exit 1
fi

PIP_VERSION=$(python3 -m pip --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}   ✅ pip $PIP_VERSION encontrado${NC}"
echo ""

# ============================================================================
# PASO 2: CREAR ENTORNO VIRTUAL
# ============================================================================
echo -e "${CYAN}[2/8] 📦 Configurando entorno virtual Python...${NC}"
echo ""

if [ -d ".venv" ]; then
    echo -e "${YELLOW}   ℹ️  El entorno virtual ya existe en: .venv/${NC}"
    echo -e "${YELLOW}   ℹ️  Se usará el entorno existente${NC}"
else
    echo "   ⏳ Creando entorno virtual (esto toma ~10 segundos)..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}   ❌ ERROR: No se pudo crear el entorno virtual${NC}"
        echo ""
        echo -e "${YELLOW}💡 POSIBLES CAUSAS:${NC}"
        echo "   - Falta python3-venv: sudo apt-get install python3-venv"
        echo "   - Permisos insuficientes"
        echo "   - Espacio en disco insuficiente"
        echo ""
        exit 1
    fi
    echo -e "${GREEN}   ✅ Entorno virtual creado correctamente${NC}"
fi
echo ""

# ============================================================================
# PASO 3: ACTIVAR ENTORNO VIRTUAL
# ============================================================================
echo -e "${CYAN}[3/8] 🔌 Activando entorno virtual...${NC}"
echo ""

if [ ! -f ".venv/bin/activate" ]; then
    echo -e "${RED}   ❌ ERROR: No se encontró el script de activación${NC}"
    echo -e "${YELLOW}   ℹ️  Ruta esperada: .venv/bin/activate${NC}"
    exit 1
fi

source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}   ❌ ERROR: No se pudo activar el entorno virtual${NC}"
    exit 1
fi

echo -e "${GREEN}   ✅ Entorno virtual activado${NC}"
echo -e "${GREEN}   ℹ️  Ruta: $VIRTUAL_ENV${NC}"
echo ""

# ============================================================================
# PASO 4: ACTUALIZAR PIP
# ============================================================================
echo -e "${CYAN}[4/8] ⬆️  Actualizando pip a la última versión...${NC}"
echo ""

python -m pip install --upgrade pip --quiet
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}   ⚠️  No se pudo actualizar pip, usando versión actual${NC}"
else
    echo -e "${GREEN}   ✅ pip actualizado correctamente${NC}"
fi
echo ""

# ============================================================================
# PASO 5: INSTALAR DEPENDENCIAS DE PYTHON
# ============================================================================
echo -e "${CYAN}[5/8] 📚 Instalando dependencias de Python...${NC}"
echo "   ℹ️  Leyendo requirements.txt"
echo ""

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}   ❌ ERROR: No se encontró el archivo requirements.txt${NC}"
    exit 1
fi

echo "   📦 Instalando: playwright, python-dotenv, apscheduler, psutil"
echo "   ⏳ Esto puede tomar 30-60 segundos dependiendo de su conexión..."
echo ""

python -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}   ❌ ERROR CRÍTICO: Falló la instalación de dependencias${NC}"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${YELLOW}💡 POSIBLES CAUSAS Y SOLUCIONES:${NC}"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "1. Sin conexión a Internet"
    echo "   → Verifique su conexión"
    echo ""
    echo "2. Falta compilador o dependencias del sistema"
    echo "   → Ubuntu/Debian: sudo apt-get install build-essential python3-dev"
    echo "   → Fedora/RHEL: sudo dnf groupinstall \"Development Tools\""
    echo ""
    echo "3. Archivo requirements.txt dañado"
    echo "   → Re-descargue el proyecto"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    exit 1
fi

echo -e "${GREEN}   ✅ Todas las dependencias instaladas correctamente${NC}"
echo ""

# Verificar instalación de paquetes críticos
python -c "import playwright; print('   ✅ playwright:', playwright.__version__)" 2>/dev/null || echo -e "${YELLOW}   ⚠️  playwright: verificación fallida${NC}"
python -c "import dotenv; print('   ✅ python-dotenv: instalado')" 2>/dev/null || echo -e "${YELLOW}   ⚠️  python-dotenv: verificación fallida${NC}"
python -c "import apscheduler; print('   ✅ apscheduler: instalado')" 2>/dev/null || echo -e "${YELLOW}   ⚠️  apscheduler: verificación fallida${NC}"
python -c "import psutil; print('   ✅ psutil: instalado')" 2>/dev/null || echo -e "${YELLOW}   ⚠️  psutil: verificación fallida${NC}"

echo ""

# ============================================================================
# PASO 6: INSTALAR NAVEGADORES DE PLAYWRIGHT
# ============================================================================
echo -e "${CYAN}[6/8] 🌐 Instalando navegador Chromium para Playwright...${NC}"
echo "   ℹ️  Se descargarán aproximadamente 170 MB"
echo "   ⏳ Esto puede tomar 2-5 minutos dependiendo de su conexión..."
echo ""

python -m playwright install chromium
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}   ❌ ERROR: Falló la instalación del navegador Chromium${NC}"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${YELLOW}💡 SOLUCIONES:${NC}"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "1. Verifique su conexión a Internet"
    echo ""
    echo "2. Instale dependencias del sistema para Chromium:"
    echo "   Ubuntu/Debian:"
    echo "     sudo apt-get install libgbm1 libxkbcommon0 libgtk-3-0"
    echo ""
    echo "3. Intente instalar manualmente:"
    echo "   source .venv/bin/activate"
    echo "   playwright install chromium --force"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    exit 1
fi

echo -e "${GREEN}   ✅ Navegador Chromium instalado correctamente${NC}"
echo ""

# ============================================================================
# PASO 7: CONFIGURAR ARCHIVO DE CREDENCIALES
# ============================================================================
echo -e "${CYAN}[7/8] 🔐 Configurando archivo de variables de entorno...${NC}"
echo ""

if [ -f ".env" ]; then
    echo -e "${YELLOW}   ℹ️  El archivo .env ya existe${NC}"
    echo ""
    read -p "¿Desea reemplazarlo con la plantilla? (s/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "${GREEN}   ✅ Archivo .env reemplazado desde .env.example${NC}"
        else
            echo -e "${YELLOW}   ⚠️  .env.example no encontrado, creando .env básico${NC}"
            cat > .env << 'EOF'
# Configuración GeoVictoria
# IMPORTANTE: Reemplace con sus credenciales reales

GEOVICTORIA_USER=su_usuario_aqui
GEOVICTORIA_PASSWORD=su_contraseña_aqui
EOF
            echo -e "${GREEN}   ✅ Archivo .env básico creado${NC}"
        fi
    else
        echo -e "${YELLOW}   ⏭️  Se mantendrá el archivo .env existente${NC}"
    fi
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}   ✅ Archivo .env creado desde .env.example${NC}"
    else
        echo -e "${YELLOW}   ⚠️  .env.example no encontrado, creando .env básico${NC}"
        cat > .env << 'EOF'
# Configuración GeoVictoria
# IMPORTANTE: Reemplace con sus credenciales reales

GEOVICTORIA_USER=su_usuario_aqui
GEOVICTORIA_PASSWORD=su_contraseña_aqui
EOF
        echo -e "${GREEN}   ✅ Archivo .env básico creado${NC}"
    fi
fi
echo ""

# ============================================================================
# PASO 8: VERIFICACIÓN FINAL
# ============================================================================
echo -e "${CYAN}[8/8] ✔️  Verificando instalación completa...${NC}"
echo ""

ERROR_COUNT=0

# Verificar entorno virtual
if [ -f ".venv/bin/python" ]; then
    echo -e "${GREEN}   ✅ Entorno virtual: OK${NC}"
else
    echo -e "${RED}   ❌ Entorno virtual: ERROR${NC}"
    ((ERROR_COUNT++))
fi

# Verificar dependencias críticas
if python -c "import playwright, dotenv, apscheduler, psutil" 2>/dev/null; then
    echo -e "${GREEN}   ✅ Dependencias: OK${NC}"
else
    echo -e "${RED}   ❌ Dependencias: INCOMPLETAS${NC}"
    ((ERROR_COUNT++))
fi

# Verificar archivo .env
if [ -f ".env" ]; then
    echo -e "${GREEN}   ✅ Archivo .env: OK${NC}"
else
    echo -e "${RED}   ❌ Archivo .env: NO EXISTE${NC}"
    ((ERROR_COUNT++))
fi

# Verificar archivos principales
if [ -f "src/geovictoria.py" ]; then
    echo -e "${GREEN}   ✅ Código fuente: OK${NC}"
else
    echo -e "${RED}   ❌ Código fuente: FALTA src/geovictoria.py${NC}"
    ((ERROR_COUNT++))
fi

echo ""

if [ $ERROR_COUNT -gt 0 ]; then
    echo -e "${YELLOW}   ⚠️  Se encontraron $ERROR_COUNT problema(s)${NC}"
    echo -e "${YELLOW}   ℹ️  El sistema puede no funcionar correctamente${NC}"
    echo ""
else
    echo -e "${GREEN}   ✅ Todas las verificaciones pasaron correctamente${NC}"
    echo ""
fi

# ============================================================================
# INSTALACIÓN COMPLETADA
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}║          ✅ ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!              ║${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "📋 PRÓXIMOS PASOS (IMPORTANTE):"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "PASO 1: Configurar sus credenciales (OBLIGATORIO)"
echo "────────────────────────────────────────────────────────────────"
echo ""
echo "   Edite el archivo .env con sus credenciales de GeoVictoria:"
echo ""
echo "   📝 Con nano:"
echo "      nano .env"
echo ""
echo "   📝 Con vim:"
echo "      vim .env"
echo ""
echo "   📝 Con VS Code:"
echo "      code .env"
echo ""
echo "   Reemplace estas líneas:"
echo "      GEOVICTORIA_USER=su_usuario_aqui"
echo "      GEOVICTORIA_PASSWORD=su_contraseña_aqui"
echo ""
echo "   Con sus datos reales, por ejemplo:"
echo "      GEOVICTORIA_USER=juan.perez"
echo "      GEOVICTORIA_PASSWORD=MiContraseña123"
echo ""
echo "   ⚠️  Guarde el archivo después de editar"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "PASO 2: Activar el entorno virtual (en cada nueva terminal)"
echo "────────────────────────────────────────────────────────────────"
echo ""
echo "   source .venv/bin/activate"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "PASO 3: Probar el sistema"
echo "────────────────────────────────────────────────────────────────"
echo ""
echo "   🧪 Marcaje manual (una vez):"
echo "      python src/geovictoria.py"
echo ""
echo "   ⚙️  Programador automático (recomendado):"
echo "      python src/programador.py"
echo ""
echo "   📊 Ver festivos de Colombia:"
echo "      python src/festivos_colombia.py"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "💡 CONSEJOS ÚTILES:"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "   • Para activar entorno: source .venv/bin/activate"
echo "   • Para desactivar: deactivate"
echo "   • Documentación: docs/GUIA_INSTALACION.md"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📖 DOCUMENTACIÓN ADICIONAL:"
echo ""
echo "   • README.md                - Información general"
echo "   • docs/GUIA_INSTALACION.md - Guía completa"
echo "   • docs/COMO_EXPORTAR.md    - Compartir con otros"
echo "   • LEEME_PRIMERO.txt        - Inicio rápido"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🔒 IMPORTANTE - SEGURIDAD:"
echo ""
echo "   ⚠️  NO comparta el archivo .env con nadie"
echo "   ⚠️  NO suba el archivo .env a GitHub"
echo "   ✅  El archivo .gitignore ya lo protege automáticamente"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
