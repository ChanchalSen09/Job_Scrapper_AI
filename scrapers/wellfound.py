import json
from urllib.parse import quote
import config
from scrapers.base import BaseScraper
from utils.logger import get_logger
from utils.helpers import format_search_term_for_slug
logger = get_logger('scraper.wellfound')

class WellfoundScraper(BaseScraper):
    SOURCE_NAME = 'wellfound'
    BASE_URL = 'https://wellfound.com'

    async def scrape(self) -> list[dict]:
        all_jobs: list[dict] = []
        context = await self._create_context()
        try:
            page = await context.new_page()
            page.set_default_timeout(config.PAGE_TIMEOUT)
            consecutive_failures = 0
            max_consecutive_failures = 3
            for term in config.SEARCH_TERMS:
                try:
                    jobs = await self._scrape_term(page, term)
                    all_jobs.extend(jobs)
                    logger.info("[wellfound] '%s' -> %d jobs", term, len(jobs))
                    if jobs:
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning('[wellfound] %d consecutive failures — site likely blocking. Skipping remaining terms.', consecutive_failures)
                        break
                    await self._random_delay()
                except Exception as e:
                    logger.error("[wellfound] Error scraping '%s': %s", term, e)
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning('[wellfound] Too many failures — aborting scraper.')
                        break
                    continue
        finally:
            await context.close()
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        logger.info('[wellfound] Total unique jobs: %d', len(unique_jobs))
        return unique_jobs

    async def _scrape_term(self, page, term: str) -> list[dict]:
        jobs = []
        slug = format_search_term_for_slug(term)
        url = f'{self.BASE_URL}/role/l/{slug}/india'
        logger.debug('[wellfound] Navigating to: %s', url)
        if not await self._safe_goto(page, url):
            url = f'{self.BASE_URL}/jobs?query={quote(term)}'
            if not await self._safe_goto(page, url):
                return jobs
        await self._random_delay(2.0, 4.0)
        await self._scroll_page(page, scroll_count=5)
        script_jobs = await self._extract_from_scripts(page)
        if script_jobs:
            jobs.extend(script_jobs)
            return jobs
        dom_jobs = await self._extract_from_dom(page)
        jobs.extend(dom_jobs)
        return jobs

    async def _extract_from_scripts(self, page) -> list[dict]:
        jobs = []
        try:
            scripts = await page.query_selector_all("script[type='application/json']")
            for script in scripts:
                try:
                    content = await script.inner_text()
                    data = json.loads(content)
                    extracted = self._parse_json_data(data)
                    jobs.extend(extracted)
                except (json.JSONDecodeError, Exception):
                    continue
            try:
                next_data = await page.evaluate('() => window.__NEXT_DATA__ ? JSON.stringify(window.__NEXT_DATA__) : null')
                if next_data:
                    data = json.loads(next_data)
                    extracted = self._parse_json_data(data)
                    jobs.extend(extracted)
            except Exception:
                pass
        except Exception as e:
            logger.debug('[wellfound] Script extraction failed: %s', e)
        return jobs

    def _parse_json_data(self, data: dict, depth: int=0) -> list[dict]:
        jobs = []
        if depth > 10:
            return jobs
        if isinstance(data, dict):
            if self._is_job_object(data):
                job = self._extract_job_from_json(data)
                if job:
                    jobs.append(job)
            else:
                for value in data.values():
                    jobs.extend(self._parse_json_data(value, depth + 1))
        elif isinstance(data, list):
            for item in data:
                jobs.extend(self._parse_json_data(item, depth + 1))
        return jobs

    def _is_job_object(self, obj: dict) -> bool:
        job_keys = {'title', 'name', 'jobTitle', 'role'}
        company_keys = {'company', 'companyName', 'organization', 'startup'}
        has_title = bool(job_keys & set(obj.keys()))
        has_company = bool(company_keys & set(obj.keys()))
        return has_title and (has_company or 'slug' in obj or 'url' in obj)

    def _extract_job_from_json(self, obj: dict) -> dict | None:
        title = obj.get('title') or obj.get('name') or obj.get('jobTitle') or obj.get('role', '')
        if not title:
            return None
        company_data = obj.get('company') or obj.get('startup') or {}
        if isinstance(company_data, dict):
            company = company_data.get('name') or company_data.get('companyName', '')
        elif isinstance(company_data, str):
            company = company_data
        else:
            company = obj.get('companyName', 'Unknown')
        location = obj.get('location') or obj.get('locationNames') or obj.get('remote', '')
        if isinstance(location, list):
            location = ', '.join((str(l) for l in location))
        slug = obj.get('slug') or obj.get('id', '')
        url = obj.get('url') or obj.get('link', '')
        if not url and slug:
            company_slug = ''
            if isinstance(company_data, dict):
                company_slug = company_data.get('slug', '')
            if company_slug:
                url = f'{self.BASE_URL}/company/{company_slug}/jobs/{slug}'
            else:
                url = f'{self.BASE_URL}/jobs/{slug}'
        url = self._normalize_url(url)
        if not url:
            return None
        description = obj.get('description') or obj.get('descriptionHtml') or ''
        description = self._clean_text(str(description))
        return {'title': str(title).strip(), 'company': str(company).strip() or 'Unknown', 'location': str(location).strip(), 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]}

    async def _extract_from_dom(self, page) -> list[dict]:
        jobs = []
        selectors = ["div[data-test='StartupResult']", 'div.styles_component__rp_fX', "div[class*='JobListing']", "div[class*='job-listing']", "a[href*='/jobs/']", "div[class*='styles_result']"]
        for selector in selectors:
            try:
                cards = await page.query_selector_all(selector)
                if cards:
                    logger.debug('[wellfound] Found %d cards with selector: %s', len(cards), selector)
                    for card in cards[:50]:
                        job = await self._parse_dom_card(card, page)
                        if job:
                            jobs.append(job)
                    if jobs:
                        break
            except Exception as e:
                logger.debug("[wellfound] Selector '%s' failed: %s", selector, e)
                continue
        return jobs

    async def _parse_dom_card(self, card, page) -> dict | None:
        try:
            title_el = await card.query_selector('h2') or await card.query_selector("a[class*='title']") or await card.query_selector("a[href*='/jobs/']") or await card.query_selector("span[class*='title']")
            title = await title_el.inner_text() if title_el else ''
            company_el = await card.query_selector('h3') or await card.query_selector("a[href*='/company/']") or await card.query_selector("span[class*='company']")
            company = await company_el.inner_text() if company_el else 'Unknown'
            location_el = await card.query_selector("span[class*='location']") or await card.query_selector("div[class*='location']")
            location = await location_el.inner_text() if location_el else ''
            link_el = await card.query_selector("a[href*='/jobs/']") or await card.query_selector('a')
            url = ''
            if link_el:
                href = await link_el.get_attribute('href')
                if href:
                    url = href if href.startswith('http') else f'{self.BASE_URL}{href}'
            url = self._normalize_url(url)
            if not title or not url:
                return None
            desc_el = await card.query_selector("div[class*='description']")
            description = ''
            if desc_el:
                description = await desc_el.inner_text()
                description = self._clean_text(description)
            return {'title': title.strip(), 'company': company.strip(), 'location': location.strip(), 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]}
        except Exception as e:
            logger.debug('[wellfound] Error parsing card: %s', e)
            return None