import json
import config
from scrapers.base import BaseScraper
from utils.logger import get_logger
from utils.helpers import format_search_term_for_url
logger = get_logger('scraper.indeed')

class IndeedScraper(BaseScraper):
    SOURCE_NAME = 'indeed'
    BASE_URL = 'https://in.indeed.com'

    async def scrape(self) -> list[dict]:
        all_jobs: list[dict] = []
        context = await self._create_context()
        try:
            page = await context.new_page()
            page.set_default_timeout(config.PAGE_TIMEOUT)
            await page.route('**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,eot}', lambda route: route.abort())
            consecutive_failures = 0
            max_consecutive_failures = 3
            for term in config.SEARCH_TERMS:
                try:
                    jobs = await self._scrape_term(page, term)
                    all_jobs.extend(jobs)
                    logger.info("[indeed] '%s' -> %d jobs", term, len(jobs))
                    if jobs:
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning('[indeed] %d consecutive failures — skipping remaining terms.', consecutive_failures)
                        break
                    await self._random_delay()
                except Exception as e:
                    logger.error("[indeed] Error scraping '%s': %s", term, e)
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning('[indeed] Too many failures — aborting scraper.')
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
        logger.info('[indeed] Total unique jobs: %d', len(unique_jobs))
        return unique_jobs

    async def _scrape_term(self, page, term: str) -> list[dict]:
        jobs = []
        query = format_search_term_for_url(term)
        for page_num in range(config.MAX_PAGES_PER_SEARCH):
            start = page_num * 10
            url = f'{self.BASE_URL}/jobs?q={query}&l=india&fromage=7&start={start}'
            logger.debug('[indeed] Page %d: %s', page_num + 1, url)
            if not await self._safe_goto(page, url):
                break
            await self._random_delay(1.5, 3.0)
            json_jobs = await self._extract_from_json(page)
            if json_jobs:
                jobs.extend(json_jobs)
                continue
            dom_jobs = await self._extract_from_dom(page)
            jobs.extend(dom_jobs)
            has_next = await page.query_selector("a[data-testid='pagination-page-next']")
            if not has_next:
                has_next = await page.query_selector("a[aria-label='Next Page']")
            if not has_next:
                break
        return jobs

    async def _extract_from_json(self, page) -> list[dict]:
        jobs = []
        try:
            script_content = await page.evaluate("\n                () => {\n                    // Try to find mosaic provider data\n                    const scripts = document.querySelectorAll('script');\n                    for (const s of scripts) {\n                        const text = s.textContent || '';\n                        if (text.includes('jobResults') || text.includes('window._initialData')) {\n                            return text;\n                        }\n                    }\n                    return null;\n                }\n            ")
            if script_content:
                import re
                json_match = re.search('window\\._initialData\\s*=\\s*({.*?});', script_content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                    jobs.extend(self._parse_indeed_json(data))
        except Exception as e:
            logger.debug('[indeed] JSON extraction failed: %s', e)
        return jobs

    def _parse_indeed_json(self, data: dict) -> list[dict]:
        jobs = []

        def find_results(obj, depth=0):
            if depth > 8:
                return
            if isinstance(obj, dict):
                if 'jobTitle' in obj or 'title' in obj:
                    job = self._job_from_indeed_json(obj)
                    if job:
                        jobs.append(job)
                for value in obj.values():
                    find_results(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    find_results(item, depth + 1)
        find_results(data)
        return jobs

    def _job_from_indeed_json(self, obj: dict) -> dict | None:
        title = obj.get('jobTitle') or obj.get('title') or obj.get('displayTitle', '')
        if not title:
            return None
        company = obj.get('companyName') or obj.get('company', '')
        if isinstance(company, dict):
            company = company.get('name', 'Unknown')
        location = obj.get('formattedLocation') or obj.get('location') or ''
        jk = obj.get('jobkey') or obj.get('jk') or ''
        if jk:
            url = f'{self.BASE_URL}/viewjob?jk={jk}'
        else:
            url = obj.get('link') or obj.get('url', '')
        url = self._normalize_url(url)
        if not url:
            return None
        description = obj.get('snippet') or obj.get('description') or ''
        description = self._clean_text(str(description))
        return {'title': str(title).strip(), 'company': str(company).strip() or 'Unknown', 'location': str(location).strip(), 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]}

    async def _extract_from_dom(self, page) -> list[dict]:
        jobs = []
        selectors = ['div.job_seen_beacon', "div[class*='job_seen_beacon']", 'div.resultContent', 'td.resultContent', 'div[data-jk]', 'li[data-jk]']
        for selector in selectors:
            try:
                cards = await page.query_selector_all(selector)
                if cards:
                    logger.debug('[indeed] Found %d cards with selector: %s', len(cards), selector)
                    for card in cards[:20]:
                        job = await self._parse_dom_card(card)
                        if job:
                            jobs.append(job)
                    if jobs:
                        break
            except Exception as e:
                logger.debug("[indeed] Selector '%s' failed: %s", selector, e)
                continue
        return jobs

    async def _parse_dom_card(self, card) -> dict | None:
        try:
            title_el = await card.query_selector('h2.jobTitle a') or await card.query_selector('h2.jobTitle span') or await card.query_selector('a[data-jk]') or await card.query_selector('h2 a')
            title = await title_el.inner_text() if title_el else ''
            company_el = await card.query_selector("span[data-testid='company-name']") or await card.query_selector('span.companyName') or await card.query_selector('span.css-1h7lukg')
            company = await company_el.inner_text() if company_el else 'Unknown'
            location_el = await card.query_selector("div[data-testid='text-location']") or await card.query_selector('div.companyLocation')
            location = await location_el.inner_text() if location_el else ''
            link_el = await card.query_selector('h2.jobTitle a') or await card.query_selector('a[data-jk]') or await card.query_selector("a[href*='viewjob']") or await card.query_selector("a[href*='/rc/clk']")
            url = ''
            if link_el:
                href = await link_el.get_attribute('href')
                if href:
                    url = href if href.startswith('http') else f'{self.BASE_URL}{href}'
            if not url:
                jk = await card.get_attribute('data-jk')
                if jk:
                    url = f'{self.BASE_URL}/viewjob?jk={jk}'
            url = self._normalize_url(url)
            if not title or not url:
                return None
            snippet_el = await card.query_selector('div.job-snippet') or await card.query_selector("div[class*='job-snippet']") or await card.query_selector('table.jobCardShelfContainer')
            description = ''
            if snippet_el:
                description = await snippet_el.inner_text()
                description = self._clean_text(description)
            return {'title': title.strip(), 'company': company.strip(), 'location': location.strip(), 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]}
        except Exception as e:
            logger.debug('[indeed] Error parsing card: %s', e)
            return None