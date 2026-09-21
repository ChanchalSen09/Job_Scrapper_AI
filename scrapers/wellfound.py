"""
Wellfound (AngelList Talent) job scraper.

Strategy:
  1. Try slug-based URL for each search term (most reliable)
  2. Fallback to generic jobs search URL
  3. Extract jobs from __NEXT_DATA__ / application/json scripts (fast, no DOM parsing)
  4. Fallback to DOM parsing if script extraction yields nothing

v2 improvements:
  - posted_date extraction
  - work_type metadata (remote/hybrid/onsite)
  - India-targeted URLs
  - Consistent field naming with v2 pipeline
  - Better dedup using normalize_url
"""

import json
import re
from urllib.parse import quote
import config
from scrapers.base import BaseScraper
from utils.logger import get_logger
from utils.helpers import format_search_term_for_slug, normalize_url, clean_html

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

            # Use Wellfound-specific terms (slug-format, startup-friendly)
            search_terms = getattr(config, 'WELLFOUND_SEARCH_TERMS', config.SEARCH_TERMS)

            for term in search_terms:
                try:
                    jobs = await self._scrape_term(page, term)
                    all_jobs.extend(jobs)
                    logger.info("[wellfound] '%s' -> %d jobs", term, len(jobs))
                    if jobs:
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning(
                            '[wellfound] %d consecutive empty — site may be blocking. Stopping.',
                            consecutive_failures,
                        )
                        break
                    await self._random_delay()
                except Exception as e:
                    logger.error("[wellfound] Error scraping '%s': %s", term, e)
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning('[wellfound] Too many failures — aborting.')
                        break
        finally:
            await context.close()

        unique_jobs = _dedup(all_jobs)
        logger.info('[wellfound] Total unique jobs: %d', len(unique_jobs))
        return unique_jobs

    async def _scrape_term(self, page, term: str) -> list[dict]:
        jobs = []
        # Terms may already be slug-formatted (e.g. 'ai-engineer') or plain text
        slug = term if '-' in term else format_search_term_for_slug(term)

        # Try India-specific slug URL first
        url = f'{self.BASE_URL}/role/l/{slug}/india'
        logger.debug('[wellfound] Trying: %s', url)
        if not await self._safe_goto(page, url):
            # Fallback: generic search with India filter
            url = f'{self.BASE_URL}/jobs?query={quote(term)}&location=india'
            if not await self._safe_goto(page, url):
                # Last resort: plain search
                url = f'{self.BASE_URL}/jobs?query={quote(term)}'
                if not await self._safe_goto(page, url):
                    return jobs

        await self._random_delay(2.0, 4.0)
        await self._scroll_page(page, scroll_count=5)

        # Try JSON script extraction first (much faster and more reliable)
        script_jobs = await self._extract_from_scripts(page)
        if script_jobs:
            jobs.extend(script_jobs)
            return jobs

        # Fallback: DOM parsing
        dom_jobs = await self._extract_from_dom(page)
        jobs.extend(dom_jobs)
        return jobs

    # ─── JSON Extraction ───────────────────────────────────────────────────

    async def _extract_from_scripts(self, page) -> list[dict]:
        jobs = []
        try:
            # Try __NEXT_DATA__ first (most structured)
            next_data_raw = await page.evaluate(
                '() => window.__NEXT_DATA__ ? JSON.stringify(window.__NEXT_DATA__) : null'
            )
            if next_data_raw:
                data = json.loads(next_data_raw)
                extracted = self._parse_json_data(data)
                jobs.extend(extracted)
                if jobs:
                    return jobs

            # Try application/json script tags
            scripts = await page.query_selector_all("script[type='application/json']")
            for script in scripts:
                try:
                    content = await script.inner_text()
                    if not content.strip().startswith('{') and not content.strip().startswith('['):
                        continue
                    data = json.loads(content)
                    extracted = self._parse_json_data(data)
                    jobs.extend(extracted)
                except (json.JSONDecodeError, Exception):
                    continue

        except Exception as e:
            logger.debug('[wellfound] Script extraction failed: %s', e)
        return jobs

    def _parse_json_data(self, data, depth: int = 0) -> list[dict]:
        jobs = []
        if depth > 12:
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
        """Detect if a JSON object looks like a job posting."""
        job_keys = {'title', 'name', 'jobTitle', 'role', 'job_title'}
        company_keys = {'company', 'companyName', 'organization', 'startup', 'employer'}
        
        has_title = bool(job_keys & set(obj.keys()))
        has_company = bool(company_keys & set(obj.keys()))
        
        # A real job must have a company attached.
        # Otherwise, we might accidentally match the search page metadata (which has a title and a slug).
        if not (has_title and has_company):
            return False
            
        # Must have a way to generate a URL
        return 'slug' in obj or 'url' in obj or 'id' in obj or 'jobUrl' in obj

    def _extract_job_from_json(self, obj: dict) -> dict | None:
        # Title
        title = (
            obj.get('title') or obj.get('jobTitle') or obj.get('job_title') or
            obj.get('name') or obj.get('role', '')
        )
        if not title or len(str(title)) < 3:
            return None
        title = str(title).strip()

        # Company
        company_data = obj.get('company') or obj.get('startup') or obj.get('employer') or {}
        if isinstance(company_data, dict):
            company = (
                company_data.get('name') or
                company_data.get('companyName') or
                'Unknown'
            )
        elif isinstance(company_data, str):
            company = company_data
        else:
            company = obj.get('companyName', 'Unknown')
        company = str(company).strip() or 'Unknown'

        # Location
        location = (
            obj.get('location') or
            obj.get('locationNames') or
            obj.get('locations') or
            obj.get('city') or
            ''
        )
        if isinstance(location, list):
            location = ', '.join(str(loc) for loc in location)
        if obj.get('remote') is True or obj.get('remoteOk') is True:
            location = 'Remote, India' if not location else f'Remote — {location}'
        location = str(location).strip()

        # Work type
        work_type = _extract_work_type_from_json(obj, location)

        # URL
        slug = obj.get('slug') or obj.get('id') or ''
        url = obj.get('url') or obj.get('link') or obj.get('jobUrl') or ''
        if not url and slug:
            company_slug = ''
            if isinstance(company_data, dict):
                company_slug = company_data.get('slug', '')
            if company_slug:
                url = f'{self.BASE_URL}/company/{company_slug}/jobs/{slug}'
            else:
                url = f'{self.BASE_URL}/jobs/{slug}'
        url = normalize_url(str(url)) if url else ''
        if not url or 'wellfound.com' not in url:
            return None

        # Description
        description = (
            obj.get('description') or
            obj.get('descriptionHtml') or
            obj.get('jobDescription') or
            ''
        )
        description = clean_html(str(description))[:2000]

        # Posted date
        posted_date = (
            obj.get('postedAt') or
            obj.get('createdAt') or
            obj.get('publishedAt') or
            obj.get('created_at') or
            ''
        )
        if posted_date:
            posted_date = _normalize_posted_date(str(posted_date))

        return {
            'title': title,
            'company': company,
            'location': location,
            'url': url,
            'source': self.SOURCE_NAME,
            'description': description,
            'posted_date': posted_date,
            'work_type': work_type,
        }

    # ─── DOM Extraction (fallback) ─────────────────────────────────────────

    async def _extract_from_dom(self, page) -> list[dict]:
        jobs = []
        selectors = [
            "div[data-test='StartupResult']",
            "div[class*='JobListing']",
            "div[class*='job-listing']",
            "div[class*='styles_result']",
            "div[class*='jobResult']",
            "div.styles_component__rp_fX",
            "a[href*='/jobs/']",
        ]
        for selector in selectors:
            try:
                cards = await page.query_selector_all(selector)
                if not cards:
                    continue
                logger.debug('[wellfound] DOM: %d cards with selector %s', len(cards), selector)
                for card in cards[:50]:
                    job = await self._parse_dom_card(card)
                    if job:
                        jobs.append(job)
                if jobs:
                    break
            except Exception as e:
                logger.debug("[wellfound] Selector '%s' failed: %s", selector, e)
        return jobs

    async def _parse_dom_card(self, card) -> dict | None:
        try:
            title_el = (
                await card.query_selector('h2') or
                await card.query_selector("a[class*='title']") or
                await card.query_selector("a[href*='/jobs/']") or
                await card.query_selector("span[class*='title']")
            )
            title = (await title_el.inner_text()).strip() if title_el else ''
            if not title:
                return None

            company_el = (
                await card.query_selector('h3') or
                await card.query_selector("a[href*='/company/']") or
                await card.query_selector("span[class*='company']")
            )
            company = (await company_el.inner_text()).strip() if company_el else 'Unknown'

            location_el = (
                await card.query_selector("span[class*='location']") or
                await card.query_selector("div[class*='location']") or
                await card.query_selector("span[class*='remote']")
            )
            location = (await location_el.inner_text()).strip() if location_el else ''

            link_el = (
                await card.query_selector("a[href*='/jobs/']") or
                await card.query_selector('a[href]')
            )
            url = ''
            if link_el:
                href = await link_el.get_attribute('href')
                if href:
                    url = href if href.startswith('http') else f'{self.BASE_URL}{href}'
            url = normalize_url(url)
            if not url:
                return None

            desc_el = await card.query_selector("div[class*='description']")
            description = ''
            if desc_el:
                description = clean_html(await desc_el.inner_text())

            # Work type from badge/tag
            work_type = 'unknown'
            badge_el = await card.query_selector("span[class*='remote']")
            if badge_el:
                badge_text = (await badge_el.inner_text()).lower()
                if 'remote' in badge_text:
                    work_type = 'remote'
                elif 'hybrid' in badge_text:
                    work_type = 'hybrid'

            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'source': self.SOURCE_NAME,
                'description': description[:2000],
                'posted_date': '',
                'work_type': work_type,
            }
        except Exception as e:
            logger.debug('[wellfound] Error parsing DOM card: %s', e)
            return None


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _dedup(jobs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for job in jobs:
        url = job.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(job)
    return unique


def _extract_work_type_from_json(obj: dict, location: str) -> str:
    """Infer work type from JSON fields."""
    if obj.get('remote') is True or obj.get('remoteOk') is True:
        return 'remote'
    location_lower = location.lower()
    if 'remote' in location_lower:
        return 'remote'
    if 'hybrid' in location_lower:
        return 'hybrid'
    india_cities = ['bangalore', 'bengaluru', 'mumbai', 'delhi', 'hyderabad',
                    'pune', 'chennai', 'gurgaon', 'gurugram', 'noida']
    if any(city in location_lower for city in india_cities):
        return 'onsite'
    return 'unknown'


def _normalize_posted_date(raw: str) -> str:
    """Normalize ISO timestamps to relative strings where possible."""
    if not raw:
        return ''
    # If already a relative string like "2 days ago", return as-is
    if re.search(r'\d+\s+(day|week|month|hour)', raw.lower()):
        return raw
    # Strip ISO timestamp to just the date part
    m = re.match(r'(\d{4}-\d{2}-\d{2})', raw)
    return m.group(1) if m else raw[:20]