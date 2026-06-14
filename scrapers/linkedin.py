import json
import random
import asyncio
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup
import config
from scrapers.base import BaseScraper
from utils.logger import get_logger
from utils.helpers import normalize_url, clean_html
logger = get_logger('scraper.linkedin')

class LinkedInScraper(BaseScraper):
    SOURCE_NAME = 'linkedin'
    BASE_URL = 'https://www.linkedin.com'
    GUEST_API = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'
    JOB_DETAIL_API = 'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting'

    async def scrape(self) -> list[dict]:
        all_jobs: list[dict] = []
        consecutive_failures = 0
        max_consecutive_failures = 3
        for term in config.SEARCH_TERMS:
            try:
                jobs = await self._scrape_term(term)
                all_jobs.extend(jobs)
                logger.info("[linkedin] '%s' -> %d jobs", term, len(jobs))
                if jobs:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning('[linkedin] %d consecutive failures — skipping remaining terms.', consecutive_failures)
                    break
                await self._random_delay(1.5, 3.0)
            except Exception as e:
                logger.error("[linkedin] Error scraping '%s': %s", term, e)
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning('[linkedin] Too many failures — aborting scraper.')
                    break
                continue
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        logger.info('[linkedin] Total unique jobs: %d', len(unique_jobs))
        return unique_jobs

    async def _scrape_term(self, term: str) -> list[dict]:
        jobs = []
        keywords = quote_plus(term)
        for page_num in range(config.MAX_PAGES_PER_SEARCH):
            start = page_num * 25
            params = {'keywords': term, 'location': 'India', 'f_TPR': 'r86400', 'f_E': '2,3', 'f_WT': '2', 'start': start, 'sortBy': 'R'}
            try:
                html = await self._fetch_page(params)
                if not html:
                    break
                page_jobs = self._parse_job_list(html)
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
                await asyncio.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                logger.error("[linkedin] Error fetching page %d for '%s': %s", page_num + 1, term, e)
                break
        return jobs

    async def _fetch_page(self, params: dict) -> str | None:
        headers = {'User-Agent': random.choice(config.USER_AGENTS), 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.9', 'Accept-Encoding': 'gzip, deflate, br', 'Connection': 'keep-alive', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none'}
        try:
            response = requests.get(self.GUEST_API, params=params, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                logger.warning('[linkedin] Rate limited — waiting 30s...')
                await asyncio.sleep(30)
                return None
            else:
                logger.warning('[linkedin] HTTP %d from guest API', response.status_code)
                return None
        except requests.exceptions.RequestException as e:
            logger.error('[linkedin] Request error: %s', e)
            return None

    def _parse_job_list(self, html: str) -> list[dict]:
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        cards = soup.find_all('li')
        if not cards:
            cards = soup.find_all('div', class_='base-card')
        for card in cards:
            try:
                job = self._parse_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug('[linkedin] Error parsing card: %s', e)
                continue
        return jobs

    def _parse_card(self, card) -> dict | None:
        title_el = card.find('h3', class_='base-search-card__title') or card.find('h3') or card.find('a', class_='base-card__full-link')
        title = title_el.get_text(strip=True) if title_el else ''
        if not title:
            return None
        company_el = card.find('h4', class_='base-search-card__subtitle') or card.find('a', class_='hidden-nested-link') or card.find('h4')
        company = company_el.get_text(strip=True) if company_el else 'Unknown'
        location_el = card.find('span', class_='job-search-card__location') or card.find('span', class_='base-search-card__metadata')
        location = location_el.get_text(strip=True) if location_el else ''
        link_el = card.find('a', class_='base-card__full-link') or card.find('a', href=True)
        url = ''
        if link_el and link_el.get('href'):
            url = link_el['href'].split('?')[0]
            if not url.startswith('http'):
                url = f'{self.BASE_URL}{url}'
        url = normalize_url(url)
        if not url or 'linkedin.com/jobs' not in url:
            return None
        date_el = card.find('time')
        date_posted = ''
        if date_el:
            date_posted = date_el.get('datetime', '') or date_el.get_text(strip=True)
        desc_el = card.find('p', class_='base-search-card__snippet')
        description = ''
        if desc_el:
            description = clean_html(desc_el.get_text(strip=True))
        return {'title': title, 'company': company, 'location': location, 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]}

    async def _close(self) -> None:
        pass