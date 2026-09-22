"""
Telegram notifier — sends rich per-job notifications.

Format:
  🔥 STRONG MATCH — 87/100
  AI Backend Engineer
  Company: XYZ
  Location: Remote, India
  Experience: 1-3 years
  Source: LinkedIn

  Why it matches:
  ✅ Python ✅ FastAPI ✅ RAG ✅ LangGraph ✅ PostgreSQL

  Role: AI_BACKEND | Freshness: 1 day ago
  🔗 Apply: <url>
"""

import asyncio
import json
import re
from typing import Optional
import requests
import config
from utils.logger import get_logger
from utils.helpers import truncate_text

logger = get_logger('telegram')

# Band emoji mapping
BAND_EMOJI = {
    'EXCELLENT': '🔥🔥',
    'STRONG': '🔥',
    'GOOD': '✨',
    'BORDERLINE': '📌',
    'SKIP': '⬛',
}

BAND_LABEL = {
    'EXCELLENT': 'EXCELLENT MATCH',
    'STRONG': 'STRONG MATCH',
    'GOOD': 'GOOD MATCH',
    'BORDERLINE': 'BORDERLINE',
    'SKIP': 'SKIP',
}


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

        total = len(jobs)
        sent_count = 0

        # Send header
        header = self._format_header(jobs)
        await self._send_message(header)
        await asyncio.sleep(0.5)

        # Send each job as individual message
        for idx, job in enumerate(jobs, 1):
            msg = self._format_job_message(job, idx, total)
            success = await self._send_message(msg)
            if success:
                sent_count += 1
            await asyncio.sleep(1.2)  # Telegram rate limit safety

        # Send summary footer
        footer = self._format_summary(total, sent_count)
        await self._send_message(footer)

        logger.info('Telegram: sent %d/%d jobs', sent_count, total)

    # ─── Message Formatters ────────────────────────────────────────────────

    def _format_header(self, jobs: list[dict]) -> str:
        total = len(jobs)
        band_counts: dict[str, int] = {}
        for j in jobs:
            b = j.get('match_band', 'SKIP')
            band_counts[b] = band_counts.get(b, 0) + 1

        lines = [
            f'🤖 Job Hunt — {total} new match{"es" if total != 1 else ""}',
            '',
        ]
        for band in ['EXCELLENT', 'STRONG', 'GOOD']:
            if band in band_counts:
                emoji = BAND_EMOJI[band]
                lines.append(f'  {emoji} {BAND_LABEL[band]}: {band_counts[band]}')
        return '\n'.join(lines)

    def _format_job_message(self, job: dict, idx: int, total: int) -> str:
        band = job.get('match_band', 'GOOD')
        score = job.get('final_score', job.get('score', 0))
        emoji = BAND_EMOJI.get(band, '✨')
        band_label = BAND_LABEL.get(band, band).capitalize()

        # Escape markdown characters just in case
        title = job.get('title', 'Unknown').replace('*', '').replace('_', '')
        company = job.get('company', 'Unknown').replace('*', '').replace('_', '')
        location = job.get('location', 'N/A') or 'N/A'
        source = job.get('source', 'unknown').capitalize()
        url = job.get('url', '')

        # Experience display
        exp_req = job.get('experience_requirement', {})
        if isinstance(exp_req, str):
            try:
                exp_req = json.loads(exp_req) if exp_req else {}
            except Exception:
                exp_req = {}
        exp_display = _format_experience(exp_req)

        # Freshness
        freshness = _format_freshness(job.get('posted_date', ''), job.get('freshness_score'))
        posted_str = f" (Posted {freshness.lower()})" if freshness else ""

        # Matched skills
        matched_skills = job.get('matched_skills', [])
        if isinstance(matched_skills, str):
            try:
                matched_skills = json.loads(matched_skills) if matched_skills else []
            except Exception:
                matched_skills = []
        skills_block = _format_skills(matched_skills)

        lines = [
            f'{emoji} **{title}**',
            f'*{company}* • 📍 {location}',
            '',
            f'**Match Score:** {score}/100 ({band_label})',
        ]
        
        if exp_display:
            lines.append(f'**Experience:** {exp_display}')
            
        if skills_block:
            lines.append(f'**Stack:** {skills_block}')
            
        lines.append(f'**Source:** {source}{posted_str}')
        lines.append('')
        lines.append(f'🔗 [Apply Here]({url})')

        message = '\n'.join(lines)
        if len(message) > 4090:
            message = message[:4087] + '...'
        return message

    def _format_summary(self, total: int, sent: int) -> str:
        return (
            f'✅ Hunt complete\n'
            f'─────────────────────\n'
            f'📋 New qualifying jobs: {total}\n'
            f'📱 Sent via Telegram: {sent}\n'
            f'⏰ Next scan in {config.SCHEDULE_INTERVAL_HOURS}h\n'
        )

    # ─── Telegram API ──────────────────────────────────────────────────────

    async def _send_message(self, text: str, max_retries: int = 3) -> bool:
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    f'{self.api_url}/sendMessage',
                    json={
                        'chat_id': self.chat_id,
                        'text': text,
                        'parse_mode': 'Markdown',
                        'disable_web_page_preview': True,
                    },
                    timeout=30,
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        return True
                    else:
                        logger.error('Telegram API error: %s', result.get('description', 'Unknown'))
                elif response.status_code == 429:
                    retry_after = response.json().get('parameters', {}).get('retry_after', 30)
                    logger.warning('Telegram rate limited — waiting %ds...', retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.error('Telegram HTTP %d: %s', response.status_code, response.text[:200])
            except requests.exceptions.Timeout:
                logger.warning('Telegram timeout (attempt %d/%d)', attempt, max_retries)
            except requests.exceptions.RequestException as e:
                logger.error('Telegram request error (attempt %d/%d): %s', attempt, max_retries, e)

            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)

        logger.error('Failed to send Telegram message after %d attempts', max_retries)
        return False

    # ─── Console fallback ──────────────────────────────────────────────────

    def _print_jobs_to_console(self, jobs: list[dict]) -> None:
        print('\n' + '=' * 60)
        print(f'🔥 {len(jobs)} New Qualifying Jobs')
        print('=' * 60)
        for idx, job in enumerate(jobs, 1):
            band = job.get('match_band', '?')
            score = job.get('final_score', job.get('score', 0))
            print(f'\n{idx}. [{band} — {score}/100] {job.get("title", "Unknown")}')
            print(f'   🏢 {job.get("company", "Unknown")}')
            print(f'   📍 {job.get("location", "N/A")}')
            print(f'   🔌 {job.get("source", "unknown").capitalize()}')
            skills = job.get('matched_skills', [])
            if isinstance(skills, str):
                try:
                    skills = json.loads(skills) if skills else []
                except Exception:
                    skills = []
            if skills:
                print(f'   ✅ {" | ".join(s.title() for s in skills[:6])}')
            print(f'   🔗 {job.get("url", "")}')
            print('   ' + '─' * 28)
        print(f'\n✅ Total: {len(jobs)} jobs')
        print('=' * 60 + '\n')

    async def send_test_message(self) -> bool:
        if not self._is_configured():
            return False
        return await self._send_message('🤖 Job Hunter v2 is alive — profile-driven AI job discovery active! ✅')


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _format_experience(exp_req: dict) -> str:
    if not exp_req:
        return ''
    if exp_req.get('freshers_welcome'):
        return 'Freshers welcome / 0-2 years'
    lo = exp_req.get('min')
    hi = exp_req.get('max')
    is_plus = exp_req.get('is_plus', False)
    is_preferred = exp_req.get('is_preferred', False)
    suffix = ' (preferred)' if is_preferred else ''
    if lo is not None and hi is not None and lo != hi:
        return f'{lo}–{hi} years{suffix}'
    if lo is not None and is_plus:
        return f'{lo}+ years{suffix}'
    if lo is not None:
        return f'{lo} years{suffix}'
    return ''


def _format_freshness(posted_date: str, freshness_days) -> str:
    if freshness_days is not None and freshness_days != '':
        try:
            days = int(freshness_days)
            if days == 0 or days == 1:
                return 'Today'
            if days <= 3:
                return f'{days} days ago'
            if days <= 7:
                return f'{days} days ago'
            return f'{days}+ days ago'
        except (TypeError, ValueError):
            pass
    if posted_date:
        return posted_date[:30]
    return ''


def _format_skills(skills: list) -> str:
    """Format up to 8 matched skills as dots."""
    if not skills:
        return ''
    top = skills[:8]
    return ' • '.join(s.title() for s in top)