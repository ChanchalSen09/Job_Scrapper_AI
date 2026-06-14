import asyncio
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
from utils.helpers import normalize_url
logger = get_logger('processor')

class JobProcessor:

    def __init__(self):
        self.db = Database()
        self.scorer = JobScorer()
        self.filter = JobFilter()
        self.notifier = TelegramNotifier()
        self.scrapers = [LinkedInScraper(), IndeedScraper(), NaukriScraper(), CutshortScraper(), WellfoundScraper(), InstahyreScraper()]

    async def run(self) -> None:
        start_time = datetime.now()
        logger.info('=' * 60)
        logger.info('🚀 Job processing pipeline started at %s', start_time.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info('=' * 60)
        self.db.cleanup_old_jobs(config.JOB_RETENTION_DAYS)
        raw_jobs = await self._scrape_all()
        logger.info('📋 Total raw jobs collected: %d', len(raw_jobs))
        if not raw_jobs:
            logger.info('No jobs found from any source. Pipeline complete.')
            return
        for job in raw_jobs:
            job['url'] = normalize_url(job.get('url', ''))
        raw_jobs = [j for j in raw_jobs if j.get('url')]
        logger.info('📋 Jobs with valid URLs: %d', len(raw_jobs))
        filtered_jobs = self.filter.filter_jobs(raw_jobs)
        logger.info('🔍 Jobs after filtering: %d', len(filtered_jobs))
        scored_jobs = self.scorer.score_and_attach(filtered_jobs)
        logger.info('⭐ Jobs scored and sorted')
        qualified_jobs = [j for j in scored_jobs if j.get('score', 0) >= config.MIN_SCORE_THRESHOLD]
        logger.info('🎯 Jobs above minimum score (%d): %d', config.MIN_SCORE_THRESHOLD, len(qualified_jobs))
        new_jobs = self._save_new_jobs(qualified_jobs)
        logger.info('💾 New jobs saved to database: %d', len(new_jobs))
        if new_jobs:
            await self._notify(new_jobs)
        else:
            logger.info('📭 No new jobs to notify about')
        elapsed = (datetime.now() - start_time).total_seconds()
        stats = self.db.get_stats()
        logger.info('─' * 60)
        logger.info('📊 Pipeline Summary:')
        logger.info('   Raw jobs scraped:  %d', len(raw_jobs))
        logger.info('   After filtering:   %d', len(filtered_jobs))
        logger.info('   Above threshold:   %d', len(qualified_jobs))
        logger.info('   New jobs saved:    %d', len(new_jobs))
        logger.info('   Total in database: %d', stats.get('total', 0))
        logger.info('   Time elapsed:      %.1fs', elapsed)
        logger.info('=' * 60)

    async def _scrape_all(self) -> list[dict]:
        all_jobs: list[dict] = []
        for scraper in self.scrapers:
            try:
                logger.info('🕷️  Starting %s scraper...', scraper.SOURCE_NAME)
                jobs = await scraper.run()
                all_jobs.extend(jobs)
                logger.info('✅ %s scraper completed: %d jobs', scraper.SOURCE_NAME, len(jobs))
            except Exception as e:
                logger.error('❌ %s scraper FAILED: %s', scraper.SOURCE_NAME, str(e), exc_info=True)
                continue
        return all_jobs

    def _save_new_jobs(self, jobs: list[dict]) -> list[dict]:
        new_jobs = []
        for job in jobs:
            url = job.get('url', '')
            if not url:
                continue
            if not self.db.job_exists(url):
                inserted = self.db.insert_job(job)
                if inserted:
                    new_jobs.append(job)
        return new_jobs

    async def _notify(self, jobs: list[dict]) -> None:
        try:
            await self.notifier.send_jobs(jobs)
            logger.info('📱 Telegram notifications sent for %d jobs', len(jobs))
            unnotified = self.db.get_unnotified_jobs()
            notified_urls = {j['url'] for j in jobs}
            ids_to_mark = [j['id'] for j in unnotified if j['url'] in notified_urls]
            if ids_to_mark:
                self.db.mark_notified(ids_to_mark)
        except Exception as e:
            logger.error('Failed to send Telegram notifications: %s', e, exc_info=True)