import asyncio
import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


class Config:
    LOGIN_URL = "https://clients.geovictoria.com/account/login?ReturnUrl=%2f"
    IFRAME_DOMAIN = "gvportal.geovictoria.com"
    IFRAME_TIMEOUT = 30000
    BUTTON_TIMEOUT = 5000
    MAX_RETRIES = 2
    RETRY_DELAY = 1
    HEADLESS = False
    LOGIN_TIMEOUT = 10000


# --- Selectores CSS desde config/selectors.json ---
_selectors_path = Path(__file__).parent.parent / "config" / "selectors.json"
try:
    with open(_selectors_path, "r", encoding="utf-8") as _f:
        _SEL = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    _SEL = {
        "login": {"username": "#user", "password": "input[type='password']", "submit": "#btnLogin"},
        "attendance": {
            "btn_entrada": "button[data-help-title='Marcar Entrada']:visible",
            "btn_salida": "button[data-help-title='Marcar Salida']:visible",
        },
    }

# --- Logging con rotación (5 MB x 5 archivos) ---
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"geovictoria_{datetime.now().strftime('%Y%m%d')}.log"

_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
_fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_fh, _sh])
logger = logging.getLogger(__name__)

load_dotenv()


def _tag(empleado: Optional[Dict]) -> str:
    """Prefijo de log para identificar el empleado en modo multi-empleado."""
    if empleado and empleado.get("id", "default") != "default":
        return f"[{empleado['nombre']}] "
    return ""


def get_credentials(empleado: Optional[Dict] = None):
    """Obtiene credenciales desde el dict de empleado o desde variables de entorno."""
    if empleado:
        return empleado["usuario"], empleado["password"]

    usuario = os.getenv("GEOVICTORIA_USER")
    password = os.getenv("GEOVICTORIA_PASSWORD")
    if not usuario or not password:
        logger.error("❌ Credenciales no encontradas. Configure GEOVICTORIA_USER y GEOVICTORIA_PASSWORD")
        raise ValueError("Credenciales no configuradas")
    return usuario, password


async def wait_for_iframe(page, tag: str = "", max_retries: int = 2):
    """Espera y busca el iframe con reintentos."""
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                logger.info(f"{tag}Reintentando iframe ({attempt}/{max_retries})...")

            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            await asyncio.sleep(4)

            frames_urls = [f.url for f in page.frames]
            logger.info(f"{tag}Frames disponibles (intento {attempt}): {len(page.frames)}")
            for idx, url in enumerate(frames_urls):
                logger.info(f"{tag}  Frame {idx}: {url}")

            for frame in page.frames:
                if Config.IFRAME_DOMAIN in frame.url:
                    logger.info(f"{tag}✅ Iframe encontrado: {frame.url}")
                    return frame

            if attempt < max_retries:
                logger.warning(f"{tag}Iframe no encontrado en intento {attempt}, reintentando...")
                await asyncio.sleep(3)

        except Exception as e:
            logger.warning(f"{tag}⚠️ Error buscando iframe (intento {attempt}): {e}")
            if attempt < max_retries:
                await asyncio.sleep(Config.RETRY_DELAY)

    try:
        frames_urls = [f.url for f in page.frames]
        logger.error(f"{tag}❌ Iframe no encontrado tras {max_retries} intentos. Frames: {frames_urls}")
    except Exception:
        logger.error(f"{tag}❌ Iframe no encontrado tras {max_retries} intentos")

    return None


async def login(page, usuario: str, password: str, tag: str = "") -> bool:
    """Realiza el login usando selectores configurables."""
    try:
        logger.debug(f"{tag}Navegando a login...")
        await page.goto(Config.LOGIN_URL, wait_until="domcontentloaded")

        if "browsernotsupported" in page.url:
            logger.error(f"{tag}❌ GeoVictoria detectó navegador no soportado")
            return False

        await page.fill(_SEL["login"]["username"], usuario)
        await page.fill(_SEL["login"]["password"], password)
        await page.click(_SEL["login"]["submit"])

        await page.wait_for_url(lambda url: "login" not in url, timeout=Config.LOGIN_TIMEOUT)

        if "browsernotsupported" in page.url:
            logger.error(f"{tag}❌ Redirigido a browsernotsupported tras login")
            return False

        logger.debug(f"{tag}✅ Login exitoso")
        return True

    except PlaywrightTimeoutError:
        logger.error(f"{tag}❌ Timeout en login - Verifique credenciales y conexión")
        return False
    except Exception as e:
        logger.error(f"{tag}❌ Error en login: {e}")
        return False


async def verificar_boton_disponible(target_frame, tag: str = "") -> Optional[str]:
    """Verifica qué botón de marcaje está disponible sin ejecutarlo."""
    try:
        btn = target_frame.locator(_SEL["attendance"]["btn_entrada"])
        await btn.wait_for(timeout=Config.BUTTON_TIMEOUT, state="visible")
        logger.debug(f"{tag}🔍 Botón disponible: Marcar Entrada")
        return "Entrada"
    except PlaywrightTimeoutError:
        pass

    try:
        btn = target_frame.locator(_SEL["attendance"]["btn_salida"])
        await btn.wait_for(timeout=Config.BUTTON_TIMEOUT, state="visible")
        logger.debug(f"{tag}🔍 Botón disponible: Marcar Salida")
        return "Salida"
    except PlaywrightTimeoutError:
        pass

    logger.warning(f"{tag}⚠️ Ningún botón de marcaje disponible")
    return None


async def marcar_asistencia(target_frame, tag: str = "") -> Optional[str]:
    """Ejecuta el marcaje de entrada o salida."""
    try:
        btn = target_frame.locator(_SEL["attendance"]["btn_entrada"])
        await btn.wait_for(timeout=Config.BUTTON_TIMEOUT, state="visible")
        logger.info(f"{tag}Haciendo clic en 'Marcar Entrada'...")
        await btn.click(force=True)
        await asyncio.sleep(1)
        logger.info(f"{tag}✅ Marcaje de Entrada realizado")
        return "Entrada"

    except PlaywrightTimeoutError:
        pass

    try:
        btn = target_frame.locator(_SEL["attendance"]["btn_salida"])
        await btn.wait_for(timeout=Config.BUTTON_TIMEOUT, state="visible")
        logger.info(f"{tag}Haciendo clic en 'Marcar Salida'...")
        await btn.click(force=True)
        await asyncio.sleep(1)
        logger.info(f"{tag}✅ Marcaje de Salida realizado")
        return "Salida"

    except PlaywrightTimeoutError:
        logger.warning(f"{tag}❌ Ningún botón de marcaje disponible")
    except Exception as e:
        logger.error(f"{tag}❌ Error al marcar salida: {e}")

    return None


def _crear_contexto_browser():
    """Parámetros comunes del contexto de navegador."""
    return {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "locale": "es-CO",
        "timezone_id": "America/Bogota",
    }


async def verificar_estado(empleado: Optional[Dict] = None) -> Optional[str]:
    """Verifica qué botón está disponible en GeoVictoria sin ejecutar marcaje."""
    tag = _tag(empleado)
    try:
        usuario, password = get_credentials(empleado)
        logger.debug(f"{tag}🔍 Verificando estado...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage", "--no-sandbox"],
            )
            context = await browser.new_context(**_crear_contexto_browser())
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await context.new_page()

            try:
                if not await login(page, usuario, password, tag=tag):
                    return None

                target_frame = await wait_for_iframe(page, tag=tag, max_retries=Config.MAX_RETRIES)
                if not target_frame:
                    return None

                return await verificar_boton_disponible(target_frame, tag=tag)
            finally:
                await browser.close()

    except Exception as e:
        logger.error(f"{tag}❌ Error verificando estado: {e}")
        return None


async def run(accion_esperada: Optional[str] = None, empleado: Optional[Dict] = None) -> Optional[str]:
    """
    Ejecuta el marcaje de asistencia.

    Args:
        accion_esperada: "Entrada" o "Salida". Si se especifica, solo ejecuta si coincide.
                         None = ejecuta lo que esté disponible (modo manual).
        empleado: Dict de configuración del empleado. None = usa variables de entorno.
    """
    tag = _tag(empleado)
    accion = None

    try:
        usuario, password = get_credentials(empleado)
        logger.info("=" * 60)
        logger.info(f"{tag}Iniciando marcaje GeoVictoria")
        logger.info(f"{tag}Usuario: {usuario}")
        if accion_esperada:
            logger.info(f"{tag}Acción esperada: {accion_esperada}")
        logger.info("=" * 60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=Config.HEADLESS,
                args=["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage", "--no-sandbox"],
            )
            context = await browser.new_context(**_crear_contexto_browser())
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await context.new_page()

            try:
                if not await login(page, usuario, password, tag=tag):
                    logger.error(f"{tag}❌ Fallo en login")
                    return None

                target_frame = await wait_for_iframe(page, tag=tag, max_retries=Config.MAX_RETRIES)
                if not target_frame:
                    logger.error(f"{tag}❌ No se encontró el iframe")
                    return None

                if accion_esperada:
                    boton_disponible = await verificar_boton_disponible(target_frame, tag=tag)
                    if boton_disponible != accion_esperada:
                        logger.warning(f"{tag}⚠️ Validación fallida: esperado='{accion_esperada}', disponible='{boton_disponible or 'Ninguno'}' - No se ejecutará")
                        return None

                accion = await marcar_asistencia(target_frame, tag=tag)

                if accion:
                    logger.info(f"{tag}✅ MARCAJE EXITOSO: {accion} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    logger.warning(f"{tag}⚠️ NO SE REALIZÓ MARCAJE - Sin botones disponibles")

                if not Config.HEADLESS and accion:
                    await asyncio.sleep(2)

            finally:
                await browser.close()

    except ValueError as e:
        logger.error(f"{tag}❌ Error de configuración: {e}")
    except Exception as e:
        logger.error(f"{tag}❌ Error inesperado: {e}", exc_info=True)

    return accion


if __name__ == "__main__":
    asyncio.run(run())
