import asyncio
from typing import Optional
import requests
import config
from utils.logger import get_logger
from utils.helpers import truncate_text
logger = get_logger('telegram')

class TelegramNotifier:

    def __init__(self):
        self.bot_token = config.BOT_TOKEN
        self.chat_id = config.CHAT_ID
        self.batch_size = config.NOTIFICATION_BATCH_SIZE
        self.api_url = f'https://api.telegram.org/bot{self.bot_token}'

    def _is_configured(self) -> bool:
        if not self.bot_token or self.bot_token == 'your_telegram_bot_token_here':
            logger.warning('Telegram BOT_TOKEN not configured. Skipping notifications.')
            return False
        if not self.chat_id or self.chat_id == 'your_telegram_chat_id_here':
            logger.warning('Telegram CHAT_ID not configured. Skipping notifications.')
            return False
        return True

    async def send_jobs(self, jobs: list[dict]) -> None:
        if not self._is_configured():
            logger.info('Telegram not configured — printing jobs to console instead')
            self._print_jobs_to_console(jobs)
            return
        if not jobs:
            return
        total_jobs = len(jobs)
        batches = [jobs[i:i + self.batch_size] for i in range(0, len(jobs), self.batch_size)]
        sent_count = 0
        for (batch_idx, batch) in enumerate(batches, 1):
            message = self._format_batch_message(batch, batch_idx, len(batches), total_jobs)
            success = await self._send_message(message)
            if success:
                sent_count += len(batch)
            await asyncio.sleep(1.0)
        summary = self._format_summary(total_jobs, sent_count)
        await self._send_message(summary)
        logger.info('Telegram: sent %d/%d jobs in %d batches', sent_count, total_jobs, len(batches))

    def _format_batch_message(self, jobs: list[dict], batch_num: int, total_batches: int, total_jobs: int) -> str:
        if total_batches == 1:
            header = f"🔥 {total_jobs} New Matching Job{('s' if total_jobs > 1 else '')}\n"
        else:
            header = f'🔥 Batch {batch_num}/{total_batches} ({total_jobs} total jobs)\n'
        lines = [header, '']
        for (idx, job) in enumerate(jobs, 1):
            title = job.get('title', 'Unknown')
            company = job.get('company', 'Unknown')
            location = job.get('location', 'N/A') or 'N/A'
            source = job.get('source', 'unknown').capitalize()
            score = job.get('score', 0)
            url = job.get('url', '')
            job_block = f'{idx}. {title}\n   🏢 Company: {company}\n   📍 Location: {location}\n   📊 Source: {source}\n   ⭐ Score: {score}\n\n   🔗 Apply: {url}\n'
            lines.append(job_block)
            lines.append('───────────────────\n')
        message = '\n'.join(lines)
        if len(message) > 4090:
            message = message[:4087] + '...'
        return message

    def _format_summary(self, total: int, sent: int) -> str:
        return f'✅ Job Hunt Summary\n───────────────────\n📋 Total new jobs found: {total}\n📱 Successfully sent: {sent}\n🕐 Next scan in {config.SCHEDULE_INTERVAL_HOURS} hours\n'

    async def _send_message(self, text: str, max_retries: int=3) -> bool:
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(f'{self.api_url}/sendMessage', json={'chat_id': self.chat_id, 'text': text, 'disable_web_page_preview': True}, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        return True
                    else:
                        logger.error('Telegram API error: %s', result.get('description', 'Unknown'))
                elif response.status_code == 429:
                    retry_after = response.json().get('parameters', {}).get('retry_after', 30)
                    logger.warning('Telegram rate limited. Waiting %d seconds...', retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.error('Telegram HTTP %d: %s', response.status_code, response.text[:200])
            except requests.exceptions.Timeout:
                logger.warning('Telegram request timeout (attempt %d/%d)', attempt, max_retries)
            except requests.exceptions.RequestException as e:
                logger.error('Telegram request error (attempt %d/%d): %s', attempt, max_retries, e)
            if attempt < max_retries:
                wait = 2 ** attempt
                await asyncio.sleep(wait)
        logger.error('Failed to send Telegram message after %d attempts', max_retries)
        return False

    def _print_jobs_to_console(self, jobs: list[dict]) -> None:
        print('\n' + '=' * 60)
        print(f'🔥 {len(jobs)} New Matching Jobs')
        print('=' * 60)
        for (idx, job) in enumerate(jobs, 1):
            print(f"\n{idx}. {job.get('title', 'Unknown')}")
            print(f"   🏢 Company: {job.get('company', 'Unknown')}")
            print(f"   📍 Location: {job.get('location', 'N/A')}")
            print(f"   📊 Source: {job.get('source', 'unknown').capitalize()}")
            print(f"   ⭐ Score: {job.get('score', 0)}")
            print(f"   🔗 Apply: {job.get('url', '')}")
            print('   ───────────────────')
        print(f'\n✅ Total: {len(jobs)} jobs')
        print('=' * 60 + '\n')

    async def send_test_message(self) -> bool:
        if not self._is_configured():
            return False
        return await self._send_message('🤖 Job Hunter Bot is alive and configured! ✅')