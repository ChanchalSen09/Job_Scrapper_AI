import asyncio
import random
from abc import ABC, abstractmethod
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import config
from utils.logger import get_logger
from utils.helpers import normalize_url, clean_html
logger = get_logger('scraper.base')

class BaseScraper(ABC):
    SOURCE_NAME: str = 'unknown'

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def _start_browser(self) -> Browser:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled', '--disable-dev-shm-usage', '--no-sandbox', '--disable-gpu', '--disable-extensions'])
        logger.debug('[%s] Browser launched', self.SOURCE_NAME)
        return self._browser

    async def _create_context(self) -> BrowserContext:
        if not self._browser:
            await self._start_browser()
        user_agent = random.choice(config.USER_AGENTS)
        context = await self._browser.new_context(user_agent=user_agent, viewport={'width': 1920, 'height': 1080}, locale='en-US', timezone_id='Asia/Kolkata', java_script_enabled=True, ignore_https_errors=True)
        try:
            from playwright_stealth import stealth_async
            await stealth_async(context)
            logger.debug('[%s] Stealth mode applied', self.SOURCE_NAME)
        except ImportError:
            logger.warning('[%s] playwright-stealth not installed, running without stealth', self.SOURCE_NAME)
        return context

    async def _safe_goto(self, page: Page, url: str, max_retries: int=3) -> bool:
        for attempt in range(1, max_retries + 1):
            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=config.NAVIGATION_TIMEOUT)
                if response and response.status < 400:
                    logger.debug('[%s] Loaded: %s (status: %d)', self.SOURCE_NAME, url, response.status)
                    return True
                elif response:
                    logger.warning('[%s] HTTP %d for %s (attempt %d/%d)', self.SOURCE_NAME, response.status, url, attempt, max_retries)
            except Exception as e:
                logger.warning('[%s] Navigation error for %s (attempt %d/%d): %s', self.SOURCE_NAME, url, attempt, max_retries, str(e))
            if attempt < max_retries:
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.debug('[%s] Retrying in %.1fs...', self.SOURCE_NAME, wait)
                await asyncio.sleep(wait)
        logger.error('[%s] Failed to load %s after %d attempts', self.SOURCE_NAME, url, max_retries)
        return False

    async def _random_delay(self, min_s: Optional[float]=None, max_s: Optional[float]=None) -> None:
        min_delay = min_s or config.REQUEST_DELAY[0]
        max_delay = max_s or config.REQUEST_DELAY[1]
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)

    async def _scroll_page(self, page: Page, scroll_count: int=3) -> None:
        for i in range(scroll_count):
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await asyncio.sleep(random.uniform(0.5, 1.5))

    def _normalize_url(self, url: str) -> str:
        return normalize_url(url)

    def _clean_text(self, text: str) -> str:
        return clean_html(text)

    async def _close(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.debug('[%s] Browser closed', self.SOURCE_NAME)
        except Exception as e:
            logger.error('[%s] Error closing browser: %s', self.SOURCE_NAME, e)

    @abstractmethod
    async def scrape(self) -> list[dict]:
        pass

    async def run(self) -> list[dict]:
        jobs = []
        try:
            logger.info('[%s] Scraper started', self.SOURCE_NAME)
            jobs = await self.scrape()
            logger.info('[%s] Scraper completed — found %d jobs', self.SOURCE_NAME, len(jobs))
        except Exception as e:
            logger.error('[%s] Scraper failed: %s', self.SOURCE_NAME, str(e), exc_info=True)
        finally:
            await self._close()
        return jobs