"""
LinkedIn job scraper — uses the guest job search API.

Key improvements in v2:
- Uses AI-targeted SEARCH_TERMS from config
- Removed f_WT=2 (remote-only) filter so hybrid/on-site India jobs are included
- Extracts posted_date from <time> element
- Extracts work_type metadata where available
- Better tracking-param URL normalization
- Stronger per-run deduplication
"""

import random
import asyncio
import re
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

    async def scrape(self) -> list[dict]:
        all_jobs: list[dict] = []
        consecutive_failures = 0
        max_consecutive_failures = 3

        for term in config.SEARCH_TERMS:
            try:
                jobs = await self._scrape_term(term)
                all_jobs.extend(jobs)
                logger.info("[linkedin] '%s' -> %d jobs", term, len(jobs))
                consecutive_failures = 0 if jobs else consecutive_failures + 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning('[linkedin] %d consecutive empty — skipping remaining terms.', consecutive_failures)
                    break
                await self._random_delay(1.5, 3.5)
            except Exception as e:
                logger.error("[linkedin] Error scraping '%s': %s", term, e)
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning('[linkedin] Too many failures — aborting.')
                    break

        unique_jobs = _dedup(all_jobs)
        logger.info('[linkedin] Total unique jobs: %d', len(unique_jobs))
        return unique_jobs

    async def _scrape_term(self, term: str) -> list[dict]:
        jobs = []
        for page_num in range(config.MAX_PAGES_PER_SEARCH):
            start = page_num * 25
            params = {
                'keywords': term,
                'location': 'India',
                'f_TPR': 'r604800',   # Posted in last 7 days
                'f_E': '2,3',         # Entry + Associate level
                # NOTE: f_WT removed — we now accept remote, hybrid, and on-site
                # The scorer and filter handle location quality.
                'start': start,
                'sortBy': 'R',        # Most relevant
            }
            try:
                html = await self._fetch_page(params)
                if not html:
                    break
                page_jobs = self._parse_job_list(html)
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
                await asyncio.sleep(random.uniform(1.0, 2.5))
            except Exception as e:
                logger.error("[linkedin] Error fetching page %d for '%s': %s", page_num + 1, term, e)
                break
        return jobs

    async def _fetch_page(self, params: dict) -> str | None:
        headers = {
            'User-Agent': random.choice(config.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
        try:
            response = requests.get(
                self.GUEST_API,
                params=params,
                headers=headers,
                timeout=20,
            )
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                logger.warning('[linkedin] Rate limited — waiting 45s...')
                await asyncio.sleep(45)
                return None
            else:
                logger.warning('[linkedin] HTTP %d from guest API', response.status_code)
                return None
        except requests.exceptions.RequestException as e:
            logger.error('[linkedin] Request error: %s', e)
            return None

    def _parse_job_list(self, html: str) -> list[dict]:
        jobs = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')

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
        return jobs

    def _parse_card(self, card) -> dict | None:
        # Title
        title_el = (
            card.find('h3', class_='base-search-card__title') or
            card.find('h3') or
            card.find('a', class_='base-card__full-link')
        )
        title = title_el.get_text(strip=True) if title_el else ''
        if not title:
            return None

        # Company
        company_el = (
            card.find('h4', class_='base-search-card__subtitle') or
            card.find('a', class_='hidden-nested-link') or
            card.find('h4')
        )
        company = company_el.get_text(strip=True) if company_el else 'Unknown'

        # Location
        location_el = (
            card.find('span', class_='job-search-card__location') or
            card.find('span', class_='base-search-card__metadata')
        )
        location = location_el.get_text(strip=True) if location_el else ''

        # URL — normalize to strip tracking params
        link_el = (
            card.find('a', class_='base-card__full-link') or
            card.find('a', href=True)
        )
        url = ''
        if link_el and link_el.get('href'):
            raw_href = link_el['href']
            # Strip everything after '?' and clean tracking
            raw_href = raw_href.split('?')[0]
            if not raw_href.startswith('http'):
                raw_href = f'{self.BASE_URL}{raw_href}'
            url = normalize_url(raw_href)

        if not url or 'linkedin.com/jobs' not in url:
            return None

        # Posted date
        date_el = card.find('time')
        posted_date = ''
        if date_el:
            posted_date = (
                date_el.get('datetime', '') or
                date_el.get_text(strip=True)
            )

        # Description snippet
        desc_el = card.find('p', class_='base-search-card__snippet')
        description = ''
        if desc_el:
            description = clean_html(desc_el.get_text(strip=True))

        # Work type metadata (badge if present)
        work_type = ''
        badge_el = card.find('span', class_='job-search-card__benefits') or \
                   card.find('span', string=re.compile(r'Remote|Hybrid|On-site', re.I))
        if badge_el:
            badge_text = badge_el.get_text(strip=True).lower()
            if 'remote' in badge_text:
                work_type = 'remote'
            elif 'hybrid' in badge_text:
                work_type = 'hybrid'
            elif 'on-site' in badge_text or 'onsite' in badge_text:
                work_type = 'onsite'

        return {
            'title': title,
            'company': company,
            'location': location,
            'url': url,
            'source': self.SOURCE_NAME,
            'description': description[:2000],
            'posted_date': posted_date,
            'work_type': work_type,
        }

    async def _close(self) -> None:
        # LinkedIn scraper uses requests, not Playwright
        pass


def _dedup(jobs: list[dict]) -> list[dict]:
    """Remove duplicate URLs within a single scrape run."""
    seen: set[str] = set()
    unique: list[dict] = []
    for job in jobs:
        url = job.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(job)
    return unique