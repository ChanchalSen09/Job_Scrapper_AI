import json
import config
from scrapers.base import BaseScraper
from utils.logger import get_logger
logger = get_logger('scraper.cutshort')

class CutshortScraper(BaseScraper):
    SOURCE_NAME = 'cutshort'
    BASE_URL = 'https://cutshort.io'

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
                    if '/api/' in url and ('job' in url.lower() or 'search' in url.lower()):
                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')
                            if 'json' in content_type:
                                body = await response.json()
                                extracted = self._parse_api_response(body)
                                api_jobs.extend(extracted)
                except Exception:
                    pass
            page.on('response', handle_response)
            consecutive_failures = 0
            max_consecutive_failures = 3
            for term in config.SEARCH_TERMS:
                try:
                    api_jobs.clear()
                    jobs = await self._scrape_term(page, term, api_jobs)
                    all_jobs.extend(jobs)
                    logger.info("[cutshort] '%s' -> %d jobs", term, len(jobs))
                    if jobs:
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning('[cutshort] %d consecutive failures — skipping remaining terms.', consecutive_failures)
                        break
                    await self._random_delay()
                except Exception as e:
                    logger.error("[cutshort] Error scraping '%s': %s", term, e)
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning('[cutshort] Too many failures — aborting scraper.')
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
        logger.info('[cutshort] Total unique jobs: %d', len(unique_jobs))
        return unique_jobs

    async def _scrape_term(self, page, term: str, api_jobs: list[dict]) -> list[dict]:
        jobs = []
        search_query = term.lower().replace(' ', '-')
        url = f'{self.BASE_URL}/jobs/{search_query}'
        logger.debug('[cutshort] Navigating to: %s', url)
        if not await self._safe_goto(page, url):
            url = f"{self.BASE_URL}/jobs?search={term.replace(' ', '+')}"
            if not await self._safe_goto(page, url):
                return jobs
        await self._random_delay(2.0, 4.0)
        await self._scroll_page(page, scroll_count=5)
        if api_jobs:
            jobs.extend(list(api_jobs))
            api_jobs.clear()
        else:
            json_jobs = await self._extract_from_scripts(page)
            if json_jobs:
                jobs.extend(json_jobs)
            else:
                dom_jobs = await self._extract_from_dom(page)
                jobs.extend(dom_jobs)
        return jobs

    def _parse_api_response(self, data) -> list[dict]:
        jobs = []
        items = []
        if isinstance(data, dict):
            items = data.get('jobs', []) or data.get('results', []) or data.get('data', [])
            if not items and 'hits' in data:
                items = data['hits']
        elif isinstance(data, list):
            items = data
        for item in items:
            try:
                if not isinstance(item, dict):
                    continue
                title = item.get('title') or item.get('jobTitle') or item.get('name', '')
                company = item.get('companyName') or item.get('company', '')
                if isinstance(company, dict):
                    company = company.get('name', 'Unknown')
                location = item.get('location') or ''
                if isinstance(location, list):
                    location = ', '.join((str(l) for l in location))
                remote = item.get('remote') or item.get('isRemote', False)
                if remote and (not location):
                    location = 'Remote'
                elif remote:
                    location = f'{location}, Remote'
                job_url = item.get('url') or item.get('applyUrl') or ''
                slug = item.get('slug') or item.get('id', '')
                if not job_url and slug:
                    job_url = f'{self.BASE_URL}/job/{slug}'
                url = self._normalize_url(job_url)
                if not title or not url:
                    continue
                description = item.get('description') or item.get('jobDescription', '')
                description = self._clean_text(str(description))
                skills = item.get('skills') or item.get('tags') or []
                if isinstance(skills, list):
                    skill_names = []
                    for s in skills:
                        if isinstance(s, dict):
                            skill_names.append(s.get('name', ''))
                        elif isinstance(s, str):
                            skill_names.append(s)
                    if skill_names:
                        description = f"{description} Skills: {', '.join(skill_names)}"
                jobs.append({'title': str(title).strip(), 'company': str(company).strip() or 'Unknown', 'location': str(location).strip(), 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]})
            except Exception as e:
                logger.debug('[cutshort] Error parsing API item: %s', e)
                continue
        return jobs

    async def _extract_from_scripts(self, page) -> list[dict]:
        jobs = []
        try:
            next_data = await page.evaluate('() => window.__NEXT_DATA__ ? JSON.stringify(window.__NEXT_DATA__) : null')
            if next_data:
                data = json.loads(next_data)
                jobs.extend(self._find_jobs_in_json(data))
            if not jobs:
                scripts = await page.query_selector_all("script[type='application/json']")
                for script in scripts:
                    try:
                        content = await script.inner_text()
                        data = json.loads(content)
                        jobs.extend(self._find_jobs_in_json(data))
                    except Exception:
                        continue
        except Exception as e:
            logger.debug('[cutshort] Script extraction failed: %s', e)
        return jobs

    def _find_jobs_in_json(self, data, depth: int=0) -> list[dict]:
        jobs = []
        if depth > 8:
            return jobs
        if isinstance(data, dict):
            if ('title' in data or 'jobTitle' in data) and ('company' in data or 'companyName' in data):
                job = self._job_from_json(data)
                if job:
                    jobs.append(job)
            else:
                for value in data.values():
                    jobs.extend(self._find_jobs_in_json(value, depth + 1))
        elif isinstance(data, list):
            for item in data:
                jobs.extend(self._find_jobs_in_json(item, depth + 1))
        return jobs

    def _job_from_json(self, obj: dict) -> dict | None:
        title = obj.get('title') or obj.get('jobTitle', '')
        if not title:
            return None
        company = obj.get('companyName') or obj.get('company', '')
        if isinstance(company, dict):
            company = company.get('name', 'Unknown')
        location = obj.get('location') or ''
        if isinstance(location, list):
            location = ', '.join((str(l) for l in location))
        url = obj.get('url') or obj.get('link', '')
        slug = obj.get('slug') or obj.get('id', '')
        if not url and slug:
            url = f'{self.BASE_URL}/job/{slug}'
        url = self._normalize_url(url)
        if not url:
            return None
        description = obj.get('description') or obj.get('jobDescription', '')
        description = self._clean_text(str(description))
        return {'title': str(title).strip(), 'company': str(company).strip() or 'Unknown', 'location': str(location).strip(), 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]}

    async def _extract_from_dom(self, page) -> list[dict]:
        jobs = []
        selectors = ["div[class*='job-card']", "div[class*='JobCard']", "div[class*='job-listing']", "article[class*='job']", "a[href*='/job/']", "div[class*='opportunity']"]
        for selector in selectors:
            try:
                cards = await page.query_selector_all(selector)
                if cards:
                    logger.debug('[cutshort] Found %d cards with selector: %s', len(cards), selector)
                    for card in cards[:30]:
                        job = await self._parse_dom_card(card, page)
                        if job:
                            jobs.append(job)
                    if jobs:
                        break
            except Exception as e:
                logger.debug("[cutshort] Selector '%s' failed: %s", selector, e)
                continue
        return jobs

    async def _parse_dom_card(self, card, page) -> dict | None:
        try:
            title_el = await card.query_selector('h3') or await card.query_selector('h2') or await card.query_selector("a[href*='/job/']") or await card.query_selector("div[class*='title']")
            title = await title_el.inner_text() if title_el else ''
            company_el = await card.query_selector("p[class*='company']") or await card.query_selector("span[class*='company']") or await card.query_selector("div[class*='company']") or await card.query_selector('h4')
            company = await company_el.inner_text() if company_el else 'Unknown'
            location_el = await card.query_selector("span[class*='location']") or await card.query_selector("div[class*='location']")
            location = await location_el.inner_text() if location_el else ''
            link_el = await card.query_selector("a[href*='/job/']") or await card.query_selector('a')
            url = ''
            if link_el:
                href = await link_el.get_attribute('href')
                if href:
                    url = href if href.startswith('http') else f'{self.BASE_URL}{href}'
            if not url:
                tag_name = await card.evaluate('el => el.tagName.toLowerCase()')
                if tag_name == 'a':
                    href = await card.get_attribute('href')
                    if href:
                        url = href if href.startswith('http') else f'{self.BASE_URL}{href}'
            url = self._normalize_url(url)
            if not title or not url:
                return None
            skill_els = await card.query_selector_all("span[class*='skill'], span[class*='tag']")
            skills = []
            for sel in skill_els:
                text = await sel.inner_text()
                if text:
                    skills.append(text.strip())
            description = f"Skills: {', '.join(skills)}" if skills else ''
            return {'title': title.strip(), 'company': company.strip(), 'location': location.strip(), 'url': url, 'source': self.SOURCE_NAME, 'description': description[:2000]}
        except Exception as e:
            logger.debug('[cutshort] Error parsing card: %s', e)
            return None