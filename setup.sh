#!/bin/bash

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║          🚀 INSTALADOR DE GEOVICTORIA                          ║"
echo "║          Sistema de Marcaje Automático                        ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar Python
echo "[1/7] 🔍 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: Python3 no está instalado${NC}"
    echo ""
    echo "Por favor instale Python3:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip python3-venv"
    echo "  macOS: brew install python3"
    exit 1
fi
python3 --version
echo -e "${GREEN}   ✅ Python encontrado${NC}"
echo ""

# Verificar pip
echo "[2/7] 🔍 Verificando pip..."
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: pip3 no está instalado${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ pip encontrado${NC}"
echo ""

# Crear entorno virtual
echo "[3/7] 📦 Creando entorno virtual..."
if [ -d ".venv" ]; then
    echo -e "${YELLOW}   ⚠️  El entorno virtual ya existe, se usará el existente${NC}"
else
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ ERROR: No se pudo crear el entorno virtual${NC}"
        exit 1
    fi
    echo -e "${GREEN}   ✅ Entorno virtual creado${NC}"
fi
echo ""

# Activar entorno virtual
echo "[4/7] 🔌 Activando entorno virtual..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ERROR: No se pudo activar el entorno virtual${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ Entorno virtual activado${NC}"
echo ""

# Actualizar pip
echo "[5/7] ⬆️  Actualizando pip..."
pip install --upgrade pip --quiet
echo -e "${GREEN}   ✅ pip actualizado${NC}"
echo ""

# Instalar dependencias
echo "[6/7] 📚 Instalando dependencias de Python..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Falló la instalación de dependencias${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ Dependencias instaladas${NC}"
echo ""

# Instalar Playwright
echo "[7/7] 🌐 Instalando navegador Chromium para Playwright..."
echo "   ⏳ Esto puede tomar unos minutos..."
playwright install chromium
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Falló la instalación de Playwright${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ Playwright instalado correctamente${NC}"
echo ""

# Configurar credenciales
echo "════════════════════════════════════════════════════════════════"
echo ""
if [ -f ".env" ]; then
    echo "📝 El archivo .env ya existe"
    echo ""
    read -p "¿Desea reemplazarlo con uno nuevo? (s/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        cp .env.example .env
        echo -e "${GREEN}   ✅ Archivo .env reemplazado${NC}"
    else
        echo -e "${YELLOW}   ⏭️  Se mantendrá el archivo .env existente${NC}"
    fi
else
    cp .env.example .env
    echo -e "${GREEN}✅ Archivo .env creado desde .env.example${NC}"
fi
echo ""

echo "════════════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}║          ✅ ¡INSTALACIÓN COMPLETADA CON ÉXITO!                 ║${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo ""
echo "   1️⃣  Edite el archivo .env con sus credenciales de GeoVictoria"
echo "      - Abra el archivo .env con un editor de texto"
echo "      - Reemplace \"su_usuario_aqui\" con su usuario"
echo "      - Reemplace \"su_contraseña_aqui\" con su contraseña"
echo "      - Guarde el archivo"
echo ""
echo "   2️⃣  Active el entorno virtual (en cada nueva terminal):"
echo "      source .venv/bin/activate"
echo ""
echo "   3️⃣  Ejecute el programa:"
echo "      - Prueba manual:     python src/geovictoria.py"
echo "      - Programador auto:  python src/programador.py"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📖 Para más información, consulte README.md"
echo ""
