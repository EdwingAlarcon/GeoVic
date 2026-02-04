import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

# Configuración
class Config:
    LOGIN_URL = "https://clients.geovictoria.com/account/login?ReturnUrl=%2f"
    IFRAME_DOMAIN = "gvportal.geovictoria.com"
    IFRAME_TIMEOUT = 60000
    BUTTON_TIMEOUT = 5000
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    HEADLESS = False

# Configurar logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"geovictoria_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

def get_credentials():
    """Obtiene credenciales desde variables de entorno o archivo .env"""
    usuario = os.getenv("GEOVICTORIA_USER")
    password = os.getenv("GEOVICTORIA_PASSWORD")
    
    if not usuario or not password:
        logger.error("❌ Credenciales no encontradas. Configure GEOVICTORIA_USER y GEOVICTORIA_PASSWORD")
        logger.info("💡 Cree un archivo .env con:")
        logger.info("   GEOVICTORIA_USER=su_usuario")
        logger.info("   GEOVICTORIA_PASSWORD=su_contraseña")
        raise ValueError("Credenciales no configuradas")
    
    return usuario, password

async def wait_for_iframe(page, max_retries=3):
    """Espera y busca el iframe con reintentos"""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Buscando iframe (intento {attempt}/{max_retries})...")
            await page.wait_for_selector("iframe", timeout=Config.IFRAME_TIMEOUT)
            
            # Esperar a que los iframes se carguen completamente
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Buscar iframe gvportal
            for frame in page.frames:
                if Config.IFRAME_DOMAIN in frame.url:
                    logger.info(f"✅ Iframe encontrado: {frame.url}")
                    return frame
            
            logger.warning(f"⚠️ Iframe no encontrado en intento {attempt}")
            if attempt < max_retries:
                await asyncio.sleep(Config.RETRY_DELAY)
                
        except PlaywrightTimeoutError as e:
            logger.warning(f"⚠️ Timeout esperando iframe (intento {attempt}): {e}")
            if attempt < max_retries:
                await asyncio.sleep(Config.RETRY_DELAY)
    
    return None

async def login(page, usuario, password):
    """Realiza el login con manejo de errores"""
    try:
        logger.info("Navegando a página de login...")
        await page.goto(Config.LOGIN_URL, wait_until="domcontentloaded")
        
        logger.info("Completando formulario de login...")
        await page.fill("#user", usuario)
        await page.fill("input[type='password']", password)
        await page.keyboard.press("Enter")
        
        logger.info("Esperando confirmación de login...")
        await page.wait_for_url(lambda url: "login" not in url, timeout=15000)
        logger.info("✅ Login exitoso")
        return True
        
    except PlaywrightTimeoutError:
        logger.error("❌ Timeout durante login - Verifique credenciales")
        return False
    except Exception as e:
        logger.error(f"❌ Error durante login: {e}")
        return False

async def verificar_boton_disponible(target_frame):
    """Verifica qué botón está disponible sin ejecutar marcaje"""
    try:
        # Verificar si está disponible Marcar Entrada
        btn_entry = target_frame.locator("text=Marcar Entrada")
        await btn_entry.wait_for(timeout=Config.BUTTON_TIMEOUT, state="visible")
        logger.info("🔍 Botón disponible: Marcar Entrada")
        return "Entrada"
    except PlaywrightTimeoutError:
        pass
    
    try:
        # Verificar si está disponible Marcar Salida
        btn_exit = target_frame.locator("text=Marcar Salida")
        await btn_exit.wait_for(timeout=Config.BUTTON_TIMEOUT, state="visible")
        logger.info("🔍 Botón disponible: Marcar Salida")
        return "Salida"
    except PlaywrightTimeoutError:
        pass
    
    logger.warning("🔍 Ningún botón de marcaje disponible")
    return None

async def marcar_asistencia(target_frame):
    """Intenta marcar entrada o salida con validación"""
    accion = None
    
    try:
        # Intentar marcar entrada
        logger.info("Buscando botón 'Marcar Entrada'...")
        btn_entry = target_frame.locator("text=Marcar Entrada")
        await btn_entry.wait_for(timeout=Config.BUTTON_TIMEOUT, state="visible")
        
        logger.info("Haciendo clic en 'Marcar Entrada'...")
        await btn_entry.click(force=True)
        accion = "Entrada"
        
        # Esperar confirmación visual
        await asyncio.sleep(2)
        logger.info("✅ Marcaje de Entrada realizado")
        
    except PlaywrightTimeoutError:
        logger.info("Botón 'Marcar Entrada' no disponible")
        
        try:
            # Intentar marcar salida
            logger.info("Buscando botón 'Marcar Salida'...")
            btn_exit = target_frame.locator("text=Marcar Salida")
            await btn_exit.wait_for(timeout=Config.BUTTON_TIMEOUT, state="visible")
            
            logger.info("Haciendo clic en 'Marcar Salida'...")
            await btn_exit.click(force=True)
            accion = "Salida"
            
            # Esperar confirmación visual
            await asyncio.sleep(2)
            logger.info("✅ Marcaje de Salida realizado")
            
        except PlaywrightTimeoutError:
            logger.warning("❌ Botón 'Marcar Salida' no disponible")
        except Exception as e:
            logger.error(f"❌ Error al marcar salida: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error al marcar entrada: {e}")
    
    return accion

async def verificar_estado():
    """Verifica qué botón está disponible en GeoVictoria sin ejecutar marcaje"""
    browser = None
    boton_disponible = None
    
    try:
        # Obtener credenciales
        usuario, password = get_credentials()
        logger.info("🔍 Verificando estado actual en GeoVictoria...")
        
        # Iniciar navegador
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)  # Siempre headless para verificación
            context = await browser.new_context()
            page = await context.new_page()
            
            # Login
            if not await login(page, usuario, password):
                logger.error("❌ Fallo en el proceso de login")
                return None
            
            # Buscar iframe
            target_frame = await wait_for_iframe(page, max_retries=Config.MAX_RETRIES)
            
            if not target_frame:
                logger.error("❌ No se pudo encontrar el iframe")
                return None
            
            # Verificar qué botón está disponible
            boton_disponible = await verificar_boton_disponible(target_frame)
            
    except Exception as e:
        logger.error(f"❌ Error verificando estado: {e}")
    finally:
        if browser:
            await browser.close()
    
    return boton_disponible

async def run():
    """Función principal con manejo completo de errores"""
    browser = None
    accion = None
    
    try:
        # Obtener credenciales
        usuario, password = get_credentials()
        logger.info("=" * 60)
        logger.info(f"Iniciando marcaje automático GeoVictoria")
        logger.info(f"Usuario: {usuario}")
        logger.info("=" * 60)
        
        # Iniciar navegador
        async with async_playwright() as p:
            logger.info("Iniciando navegador...")
            browser = await p.chromium.launch(headless=Config.HEADLESS)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Login
            if not await login(page, usuario, password):
                logger.error("❌ Fallo en el proceso de login")
                return None
            
            # Buscar iframe con reintentos
            target_frame = await wait_for_iframe(page, max_retries=Config.MAX_RETRIES)
            
            if not target_frame:
                logger.error("❌ No se pudo encontrar el iframe después de varios intentos")
                return None
            
            # Marcar asistencia
            accion = await marcar_asistencia(target_frame)
            
            if accion:
                logger.info("=" * 60)
                logger.info(f"✅ MARCAJE EXITOSO: {accion}")
                logger.info(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 60)
            else:
                logger.warning("=" * 60)
                logger.warning("⚠️ NO SE REALIZÓ MARCAJE")
                logger.warning("No se encontró botón de Entrada ni Salida disponible")
                logger.warning("=" * 60)
            
            # Mantener navegador abierto brevemente para ver resultado
            await asyncio.sleep(3)
            
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}", exc_info=True)
    finally:
        if browser:
            await browser.close()
    
    return accion

if __name__ == "__main__":
    asyncio.run(run())