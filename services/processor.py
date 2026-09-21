"""
Job processing pipeline — scrape → filter → score → deduplicate → save → notify.

Pipeline stages:
  1. Scrape all sources (fail-safe per source)
  2. Normalize and deduplicate URLs
  3. Filter jobs (location, title, experience pre-check)
  4. Score and explain (0–100 normalized)
  5. Apply freshness penalty
  6. Keep only GOOD / STRONG / EXCELLENT band (score >= 70)
  7. Save new jobs to database (dedup company+title)
  8. Send Telegram notifications
  9. Log full pipeline summary
"""

import asyncio
import json
from datetime import datetime
import config
from database.sqlite import Database
from scrapers.linkedin import LinkedInScraper
from scrapers.wellfound import WellfoundScraper
from scrapers.indeed import IndeedScraper
from scrapers.naukri import NaukriScraper
from scrapers.cutshort import CutshortScraper
from scrapers.instahyre import InstahyreScraper
from services.scorer import JobScorer
from services.filters import JobFilter
from telegram_bot.notifier import TelegramNotifier
from utils.logger import get_logger
from utils.helpers import normalize_url, normalize_title

logger = get_logger('processor')


class JobProcessor:

    def __init__(self):
        self.db = Database()
        self.scorer = JobScorer()
        self.filter = JobFilter()
        self.notifier = TelegramNotifier()
        self.scrapers = [
            LinkedInScraper(),
            # IndeedScraper(),   # Disabled due to 403 errors
            # NaukriScraper(),   # Disabled due to 403 errors
            # CutshortScraper(), # Disabled due to 403 errors
            WellfoundScraper(),
            InstahyreScraper(),
        ]

    async def run(self) -> None:
        start_time = datetime.now()
        logger.info('=' * 60)
        logger.info('🚀 Job pipeline started at %s', start_time.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info('=' * 60)

        self.db.cleanup_old_jobs(config.JOB_RETENTION_DAYS)

        # ── Stage 1: Scrape
        raw_jobs = await self._scrape_all()
        logger.info('📋 Raw jobs collected: %d', len(raw_jobs))
        if not raw_jobs:
            logger.info('No jobs found from any source. Pipeline complete.')
            return

        # ── Stage 2: URL normalization + dedup
        for job in raw_jobs:
            job['url'] = normalize_url(job.get('url', ''))
        raw_jobs = [j for j in raw_jobs if j.get('url')]
        raw_jobs = _deduplicate_urls(raw_jobs)
        logger.info('📋 After URL dedup: %d', len(raw_jobs))

        # ── Stage 3: Filter
        filtered_jobs = self.filter.filter_jobs(raw_jobs)
        logger.info('🔍 After filter: %d', len(filtered_jobs))

        # ── Stage 4: Score + Explain
        scored_jobs = self.scorer.score_and_attach(filtered_jobs)
        rejected = [j for j in scored_jobs if j.get('is_rejected')]
        non_rejected = [j for j in scored_jobs if not j.get('is_rejected')]
        logger.info('⭐ Scored: %d jobs | Hard-rejected by scorer: %d', len(non_rejected), len(rejected))

        # ── Stage 5: Freshness penalty
        for job in non_rejected:
            _apply_freshness(job)

        # ── Stage 6: Band filter — only GOOD / STRONG / EXCELLENT
        qualified_jobs = [
            j for j in non_rejected
            if j.get('match_band', '') in config.NOTIFY_BANDS
        ]
        skipped_bands = len(non_rejected) - len(qualified_jobs)
        logger.info(
            '🎯 Qualified (≥%d score): %d | Below threshold: %d',
            config.MIN_SCORE_THRESHOLD, len(qualified_jobs), skipped_bands,
        )

        # ── Stage 7: Save new jobs
        new_jobs = self._save_new_jobs(qualified_jobs)
        logger.info('💾 New jobs saved: %d', len(new_jobs))

        # ── Stage 8: Notify
        if new_jobs:
            await self._notify(new_jobs)
        else:
            logger.info('📭 No new qualifying jobs to notify about')

        # ── Stage 9: Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        stats = self.db.get_stats()
        self._log_summary(raw_jobs, filtered_jobs, scored_jobs, qualified_jobs, new_jobs, elapsed, stats)

    # ─── Scraping ──────────────────────────────────────────────────────────

    async def _scrape_all(self) -> list[dict]:
        all_jobs: list[dict] = []
        source_counts: dict[str, int] = {}
        source_errors: dict[str, str] = {}

        for scraper in self.scrapers:
            source = scraper.SOURCE_NAME
            try:
                logger.info('🕷️  Starting %s scraper...', source)
                jobs = await scraper.run()
                all_jobs.extend(jobs)
                source_counts[source] = len(jobs)
                logger.info('✅ %s: %d jobs', source, len(jobs))
            except Exception as e:
                logger.error('❌ %s scraper FAILED: %s', source, str(e), exc_info=True)
                source_errors[source] = str(e)
                source_counts[source] = 0
                continue

        logger.info('📊 Source breakdown: %s', source_counts)
        if source_errors:
            logger.warning('⚠️  Source errors: %s', source_errors)
        return all_jobs

    # ─── Save ──────────────────────────────────────────────────────────────

    def _save_new_jobs(self, jobs: list[dict]) -> list[dict]:
        new_jobs = []
        for job in jobs:
            url = job.get('url', '')
            if not url:
                continue
            title = job.get('title', '')
            company = job.get('company', '')
            if not self.db.job_exists(url, title, company):
                inserted = self.db.insert_job(job)
                if inserted:
                    new_jobs.append(job)
        return new_jobs

    # ─── Notify ────────────────────────────────────────────────────────────

    async def _notify(self, jobs: list[dict]) -> None:
        # Sort: EXCELLENT → STRONG → GOOD, then by score desc
        def sort_key(j: dict):
            band = j.get('match_band', 'SKIP')
            band_order = {'EXCELLENT': 0, 'STRONG': 1, 'GOOD': 2}.get(band, 3)
            return (band_order, -(j.get('final_score', 0)))

        sorted_jobs = sorted(jobs, key=sort_key)

        try:
            await self.notifier.send_jobs(sorted_jobs)
            logger.info('📱 Telegram notifications sent for %d jobs', len(sorted_jobs))

            # Mark as notified
            unnotified = self.db.get_unnotified_jobs()
            notified_urls = {j['url'] for j in sorted_jobs}
            ids_to_mark = [j['id'] for j in unnotified if j['url'] in notified_urls and j.get('id')]
            if ids_to_mark:
                self.db.mark_notified(ids_to_mark)
        except Exception as e:
            logger.error('Failed to send Telegram notifications: %s', e, exc_info=True)

    # ─── Logging ───────────────────────────────────────────────────────────

    def _log_summary(self, raw, filtered, scored, qualified, new_jobs, elapsed, stats):
        rejected_count = sum(1 for j in scored if j.get('is_rejected'))
        ai_relevant = sum(1 for j in scored if j.get('ai_score', 0) >= 30 and not j.get('is_rejected'))
        avg_score = (
            sum(j.get('final_score', 0) for j in qualified) / len(qualified)
            if qualified else 0
        )

        # Band breakdown in qualified
        bands: dict[str, int] = {}
        for j in qualified:
            b = j.get('match_band', 'SKIP')
            bands[b] = bands.get(b, 0) + 1

        # Role category breakdown in new_jobs
        roles: dict[str, int] = {}
        for j in new_jobs:
            r = j.get('role_category', 'UNKNOWN')
            roles[r] = roles.get(r, 0) + 1

        logger.info('─' * 60)
        logger.info('📊 PIPELINE SUMMARY')
        logger.info('   Raw scraped:        %d', len(raw))
        logger.info('   After filter:       %d', len(filtered))
        logger.info('   AI-relevant:        %d', ai_relevant)
        logger.info('   Hard-rejected:      %d', rejected_count)
        logger.info('   Qualified (≥%d):    %d', config.MIN_SCORE_THRESHOLD, len(qualified))
        logger.info('   New jobs saved:     %d', len(new_jobs))
        logger.info('   Avg score (qual.):  %.1f', avg_score)
        logger.info('   Elapsed:            %.1fs', elapsed)
        logger.info('   DB total:           %d', stats.get('total', 0))
        logger.info('   Match bands:        %s', bands)
        logger.info('   New role cats:      %s', roles)
        if stats.get('by_role'):
            logger.info('   Today by role:      %s', stats.get('by_role'))
        logger.info('=' * 60)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _deduplicate_urls(jobs: list[dict]) -> list[dict]:
    """Remove duplicate URLs within a single pipeline run."""
    seen_urls: set[str] = set()
    seen_company_title: set[tuple[str, str]] = set()
    unique: list[dict] = []

    for job in jobs:
        url = job.get('url', '')
        company = job.get('company', '').lower()
        title = normalize_title(job.get('title', ''))

        if url in seen_urls:
            continue
        ct_key = (company, title)
        if ct_key in seen_company_title and company and title:
            continue

        seen_urls.add(url)
        if company and title:
            seen_company_title.add(ct_key)
        unique.append(job)

    return unique


def _apply_freshness(job: dict) -> None:
    """
    Apply a freshness multiplier to final_score based on posted_date.
    Modifies the job dict in-place.
    """
    posted = job.get('posted_date', '')
    if not posted:
        return  # No date info — don't penalize

    # Try to parse age from relative strings like "1 day ago", "3 days ago"
    import re
    m = re.search(r'(\d+)\s*(day|week|month)', posted.lower())
    if not m:
        return

    val = int(m.group(1))
    unit = m.group(2)

    if unit == 'week':
        days = val * 7
    elif unit == 'month':
        days = val * 30
    else:
        days = val

    # Get multiplier
    if days <= 1:
        multiplier = config.FRESHNESS_WEIGHTS['0-1']
    elif days <= 3:
        multiplier = config.FRESHNESS_WEIGHTS['2-3']
    elif days <= 7:
        multiplier = config.FRESHNESS_WEIGHTS['4-7']
    elif days <= 15:
        multiplier = config.FRESHNESS_WEIGHTS['8-15']
    else:
        multiplier = config.FRESHNESS_WEIGHTS['15+']

    if multiplier == 0.0:
        # Too old — move to skip band
        job['final_score'] = 0
        job['match_band'] = 'SKIP'
        job['score'] = 0
        job['freshness_score'] = 0
        return

    original = job.get('final_score', 0)
    adjusted = round(original * multiplier)
    job['final_score'] = adjusted
    job['score'] = adjusted
    job['freshness_score'] = days

    # Recalculate band
    from services.scorer import _get_band
    job['match_band'] = _get_band(adjusted)