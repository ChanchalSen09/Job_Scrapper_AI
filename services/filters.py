"""
Job filter for Chanchal Sen's profile-driven job discovery system.

Critical fix: The old filter hard-gated on remote-only.
This version passes Remote + Hybrid India + On-site in supported cities.
The scorer handles location quality scoring.
"""

import re
import config
from utils.logger import get_logger
from utils.helpers import parse_experience_requirement, normalize_title

logger = get_logger('filters')


class JobFilter:

    def __init__(self):
        self.max_experience = config.EXPERIENCE_HARD_REJECT_MIN
        # All target role strings flattened
        self.target_titles: list[str] = []
        for tier in config.TARGET_ROLES.values():
            self.target_titles.extend([r.lower() for r in tier])

    def should_keep(self, job: dict) -> tuple[bool, str]:
        """
        Decide whether to keep a job.

        Returns (keep: bool, reason: str) where reason explains any rejection.
        """
        company = job.get('company', '').lower()
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        location = job.get('location', '').lower()
        full_text = f'{title} {description} {location}'

        # ── Banned company
        for banned in config.BANNED_COMPANIES:
            if banned.lower() in company:
                return False, f'Banned company: {company}'

        # ── Title pre-check — must relate to engineering/development/AI
        if not self._passes_title_precheck(title):
            return False, f'Title not relevant: "{job.get("title", "")}"'

        # ── Location check — remote OR India
        if not self._passes_location_check(location, full_text):
            return False, f'Unsupported location: "{job.get("location", "")}"'

        # ── Experience hard pre-filter
        exp_reject, exp_reason = self._fails_experience_precheck(full_text)
        if exp_reject:
            return False, exp_reason

        # ── Title exclusion (senior/leadership) — quick pre-filter
        for kw in config.EXCLUDED_TITLE_KEYWORDS:
            if kw in title:
                return False, f'Senior/leadership role: "{kw}" in title'

        # ── Unrelated role types in title
        for role in config.EXCLUDED_ROLE_TYPES:
            if role in title:
                return False, f'Excluded role type: {role}'

        return True, ''

    def _passes_title_precheck(self, title: str) -> bool:
        """Quick pre-check: does the title relate to any engineering/tech role?"""
        # Accept if it matches any known target role
        for role in self.target_titles:
            if role in title:
                return True
        # Accept generic tech role keywords
        broad_kws = [
            'ai', 'ml', 'machine learning', 'llm', 'genai',
            'python', 'backend', 'full stack', 'fullstack', 'full-stack',
            'engineer', 'developer', 'sde', 'software',
            'rag', 'agentic', 'generative',
        ]
        for kw in broad_kws:
            if kw in title:
                return True
        return False

    def _passes_location_check(self, location: str, full_text: str) -> bool:
        """
        Pass if job is:
        - Remote (anywhere in India)
        - Hybrid in India
        - On-site in a supported India city
        - Location unspecified (let scorer handle)
        """
        if not location or location in ('', 'unknown', 'n/a'):
            return True  # Unspecified — don't reject, let scorer penalize

        combined = f'{location} {full_text[:300]}'
        c = combined.lower()

        # Remote signals — always pass
        remote_signals = config.REMOTE_KEYWORDS + ['anywhere', 'globally']
        for sig in remote_signals:
            if sig in c:
                return True

        # Hybrid — pass if India context
        for sig in config.HYBRID_KEYWORDS:
            if sig in c:
                if 'india' in c or any(city in c for city in config.TIER_1_CITIES):
                    return True

        # On-site India cities
        all_india_cities = config.TIER_1_CITIES + config.TIER_2_CITIES + ['india']
        for city in all_india_cities:
            if city in c:
                return True

        # International remote explicitly allowing India
        if 'remote' in c and ('india' in c or any(city in c for city in all_india_cities)):
            return True

        return False

    def _fails_experience_precheck(self, text: str) -> tuple[bool, str]:
        """
        Hard-reject if minimum required experience is clearly >= EXPERIENCE_HARD_REJECT_MIN years.
        """
        exp = parse_experience_requirement(text)
        if exp.get('is_required') and exp.get('min') is not None:
            min_exp = exp['min']
            if min_exp >= self.max_experience:
                return True, f'Hard experience reject: requires {min_exp}+ years'
        return False, ''

    def filter_jobs(self, jobs: list[dict]) -> list[dict]:
        """Filter job list, logging counts and reasons."""
        kept = []
        filtered_count = 0
        rejection_reasons: dict[str, int] = {}

        for job in jobs:
            keep, reason = self.should_keep(job)
            if keep:
                kept.append(job)
            else:
                filtered_count += 1
                # Track top rejection reasons
                category = _categorize_rejection(reason)
                rejection_reasons[category] = rejection_reasons.get(category, 0) + 1
                logger.debug("Filtered '%s' @ %s — %s", job.get('title'), job.get('company'), reason)

        logger.info(
            'Filter: %d kept, %d removed (total: %d)',
            len(kept), filtered_count, len(jobs),
        )
        if rejection_reasons:
            for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
                logger.info('  Rejection reason — %s: %d', reason, count)

        return kept


def _categorize_rejection(reason: str) -> str:
    if 'banned' in reason.lower():
        return 'Banned company'
    if 'title not relevant' in reason.lower():
        return 'Irrelevant title'
    if 'location' in reason.lower():
        return 'Unsupported location'
    if 'experience' in reason.lower():
        return 'Over-experience'
    if 'senior' in reason.lower() or 'leadership' in reason.lower():
        return 'Senior/leadership role'
    if 'excluded role' in reason.lower():
        return 'Unrelated role type'
    return 'Other'