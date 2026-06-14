from scrapers.base import BaseScraper
from utils.logger import get_logger
logger = get_logger('scraper.instahyre')

class InstahyreScraper(BaseScraper):
    SOURCE_NAME = 'instahyre'
    BASE_URL = 'https://www.instahyre.com'

    async def scrape(self) -> list[dict]:
        logger.info('[instahyre] Scraper not yet implemented — skipping')
        return []