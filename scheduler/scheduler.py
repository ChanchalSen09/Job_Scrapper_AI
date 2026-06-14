import asyncio
import signal
import sys
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import config
from services.processor import JobProcessor
from utils.logger import setup_logger, get_logger
logger = get_logger('scheduler')

async def run_pipeline() -> None:
    processor = JobProcessor()
    await processor.run()

async def start_scheduler() -> None:
    setup_logger()
    logger.info('=' * 60)
    logger.info('🤖 Job Hunter System Starting')
    logger.info('   Schedule: Every %d hours', config.SCHEDULE_INTERVAL_HOURS)
    logger.info('   Database: %s', config.DATABASE_PATH)
    logger.info('   Search terms: %d configured', len(config.SEARCH_TERMS))
    logger.info('   Skills tracked: %d configured', len(config.SKILLS))
    logger.info('   Experience max: %d years', config.EXPERIENCE_MAX)
    logger.info('   Min score threshold: %d', config.MIN_SCORE_THRESHOLD)
    logger.info('=' * 60)
    from telegram_bot.notifier import TelegramNotifier
    notifier = TelegramNotifier()
    if notifier._is_configured():
        logger.info('📱 Telegram configured — sending test message...')
        success = await notifier.send_test_message()
        if success:
            logger.info('✅ Telegram test message sent successfully')
        else:
            logger.warning('⚠️  Telegram test message failed — check BOT_TOKEN and CHAT_ID')
    else:
        logger.warning('📱 Telegram not configured — jobs will be printed to console')
    logger.info('🚀 Running initial scrape...')
    await run_pipeline()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_pipeline, trigger=IntervalTrigger(hours=config.SCHEDULE_INTERVAL_HOURS), id='job_scraping_pipeline', name='Job Scraping Pipeline', max_instances=1, replace_existing=True)
    scheduler.start()
    next_run = scheduler.get_job('job_scraping_pipeline').next_run_time
    logger.info('⏰ Next scheduled run: %s', next_run.strftime('%Y-%m-%d %H:%M:%S'))
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info('🛑 Shutdown signal received (%s). Stopping scheduler...', sig)
        scheduler.shutdown(wait=False)
        shutdown_event.set()
    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, signal_handler)
    logger.info('🟢 Scheduler running. Press Ctrl+C to stop.')
    try:
        await shutdown_event.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info('🛑 Shutting down...')
        scheduler.shutdown(wait=False)
    logger.info('👋 Job Hunter System stopped.')