import json
import re
import config
from scrapers.base import BaseScraper
from utils.logger import get_logger
from utils.helpers import format_search_term_for_slug
logger = get_logger('scraper.naukri')

class NaukriScraper(BaseScraper):
    SOURCE_NAME = 'naukri'
    BASE_URL = 'https://www.naukri.com'

    async def scrape(self) -> list[dict]:
        all_jobs: list[dict] = []
        context = await self._create_context()
        try:
            page = await context.new_page()
            page.set_default_timeout(config.PAGE_TIMEOUT)
            api_jobs: list[dict] = []

            async def handle_response(response):
                try:
                    url = response.url
                    if 'jobapi' in url or 'naukri.com/jobapi' in url:
                        if response.status == 200:
                            body = await response.json()
                            extracted = self._parse_api_response(body)
                            api_jobs.extend(extracted)
                except Exception:
                    pass
            page.on('response', handle_response)
            await page.route('**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,eot}', lambda route: route.abort())
            consecutive_failures = 0
            max_consecutive_failures = 3
            for term in config.SEARCH_TERMS:
                try:
                    api_jobs.clear()
                    jobs = await self._scrape_term(page, term, api_jobs)
                    all_jobs.extend(jobs)
                    logger.info("[naukri] '%s' -> %d jobs", term, len(jobs))
                    if jobs:
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning('[naukri] %d consecutive failures — skipping remaining terms.', consecutive_failures)
                        break
                    await self._random_delay()
                except Exception as e:
                    logger.error("[naukri] Error scraping '%s': %s", term, e)
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning('[naukri] Too many failures — aborting scraper.')
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
        logger.info('[naukri] Total unique jobs: %d', len(unique_jobs))
        return unique_jobs

    async def _scrape_term(self, page, term: str, api_jobs: list[dict]) -> list[dict]:
        jobs = []
        slug = format_search_term_for_slug(term)
        for page_num in range(1, config.MAX_PAGES_PER_SEARCH + 1):
            if page_num == 1:
                url = f'{self.BASE_URL}/{slug}-jobs-in-india?experience=0'
            else:
                url = f'{self.BASE_URL}/{slug}-jobs-in-india-{page_num}?experience=0'
            logger.debug('[naukri] Page %d: %s', page_num, url)
            if not await self._safe_goto(page, url):
                break
            await self._random_delay(2.0, 4.0)
            await self._scroll_page(page, scroll_count=3)
            if api_jobs:
                jobs.extend(list(api_jobs))
                api_jobs.clear()
                continue
            dom_jobs = await self._extract_from_dom(page)
            jobs.extend(dom_jobs)
            has_next = await page.query_selector('a.fright.fs14.btn-secondary.br2')
            if not has_next:
                has_next = await page.query_selector("a[class*='btn-secondary'][href*='page']")
            if not has_next:
                break
        return jobs

    def _parse_api_response(self, data: dict) -> list[dict]:
        jobs = []
        job_details = data.get('jobDetails', [])
        if not job_details:
            job_details = data.get('results', [])
        if not job_details and isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and ('title' in value[0] or 'jobTitle' in value[0]):
                        job_details = value
                        break
        for item in job_details:
            try:
                title = item.get('title') or item.get('jobTitle', '')
                company = item.get('companyName') or item.get('company', 'Unknown')
                location = item.get('placeholders', [{}])
                if isinstance(location, list):
                    loc_parts = []
                    for ph in location:
                        if isinstance(ph, dict) and ph.get('type') == 'location':
                            loc_parts.append(ph.get('label', ''))
                    location = ', '.join(loc_parts) if loc_parts else ''
                elif isinstance(location, str):
                    pass
                else:
                    location = str(item.get('location', ''))
                jd_url = item.get('jdURL') or item.get('url') or ''
                if jd_url and (not jd_url.startswith('http')):
                    jd_url = f'{self.BASE_URL}{jd_url}'
                url = self._normalize_url(jd_url)
                if not title or not url:
                    continue
                description = item.get('jobDescription') or item.get('snippet', '')
                description = self._clean_text(str(description))
                tagsAndSkills = item.get('tagsAndSkills', '')
                if tagsAndSkills:
                    description = f'{description} Skills: {tagsAndSkills}'
                jobs.append({'title': str(title).strip(), 'company': str(company).strip(), 'location': str(location).strip(), 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]})
            except Exception as e:
                logger.debug('[naukri] Error parsing API item: %s', e)
                continue
        return jobs

    async def _extract_from_dom(self, page) -> list[dict]:
        jobs = []
        selectors = ['article.jobTuple', 'div.srp-jobtuple-wrapper', 'div.jobTupleHeader', "div[class*='jobTuple']", 'div.list', 'div.cust-job-tuple']
        for selector in selectors:
            try:
                cards = await page.query_selector_all(selector)
                if cards:
                    logger.debug('[naukri] Found %d cards with selector: %s', len(cards), selector)
                    for card in cards[:30]:
                        job = await self._parse_dom_card(card)
                        if job:
                            jobs.append(job)
                    if jobs:
                        break
            except Exception as e:
                logger.debug("[naukri] Selector '%s' failed: %s", selector, e)
                continue
        return jobs

    async def _parse_dom_card(self, card) -> dict | None:
        try:
            title_el = await card.query_selector('a.title') or await card.query_selector("a[class*='title']") or await card.query_selector('a.desig') or await card.query_selector('h2 a') or await card.query_selector("a[href*='job-listings']")
            title = await title_el.inner_text() if title_el else ''
            company_el = await card.query_selector('a.subTitle') or await card.query_selector("a[class*='comp-name']") or await card.query_selector('span.comp-name') or await card.query_selector('a.companyName')
            company = await company_el.inner_text() if company_el else 'Unknown'
            location_el = await card.query_selector('span.locWdth') or await card.query_selector("span[class*='loc']") or await card.query_selector('li.location span') or await card.query_selector('span.ni-job-tuple-icon-srp-location')
            location = await location_el.inner_text() if location_el else ''
            link_el = await card.query_selector('a.title') or await card.query_selector("a[class*='title']") or await card.query_selector('h2 a') or await card.query_selector("a[href*='naukri.com']")
            url = ''
            if link_el:
                href = await link_el.get_attribute('href')
                if href:
                    url = href if href.startswith('http') else f'{self.BASE_URL}{href}'
            url = self._normalize_url(url)
            if not title or not url:
                return None
            desc_el = await card.query_selector('span.job-desc') or await card.query_selector("div[class*='job-desc']") or await card.query_selector('span.ellipsis')
            description = ''
            if desc_el:
                description = await desc_el.inner_text()
                description = self._clean_text(description)
            skill_els = await card.query_selector_all('li.tag-li, span.tag-li, a.tag-li')
            skills = []
            for sel in skill_els:
                skill_text = await sel.inner_text()
                if skill_text:
                    skills.append(skill_text.strip())
            if skills:
                description = f"{description} Skills: {', '.join(skills)}"
            return {'title': title.strip(), 'company': company.strip(), 'location': location.strip(), 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]}
        except Exception as e:
            logger.debug('[naukri] Error parsing card: %s', e)
            return None