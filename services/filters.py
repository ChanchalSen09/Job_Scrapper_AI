import config
from utils.logger import get_logger
from utils.helpers import extract_experience
logger = get_logger('filters')

class JobFilter:

    def __init__(self):
        self.max_experience = config.EXPERIENCE_MAX
        self.skills = [s.lower() for s in config.SKILLS]
        self.target_titles = []
        for tier in config.TARGET_ROLES.values():
            self.target_titles.extend([r.lower() for r in tier])

    def should_keep(self, job: dict) -> bool:
        company = job.get('company', '').lower()
        if company in getattr(config, 'BANNED_COMPANIES', []):
            logger.debug("Filtering out job from banned company: '%s'", job.get('company'))
            return False

        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        location = job.get('location', '').lower()
        full_text = f'{title} {description} {location}'
        is_remote = any((kw in full_text for kw in ['remote', 'work from home', 'wfh', 'anywhere']))
        if not is_remote:
            return False
        if self._title_matches(title):
            return True
        exp = extract_experience(full_text)
        if exp is not None and exp > self.max_experience:
            skill_count = self._count_matching_skills(full_text)
            if skill_count >= 2:
                logger.debug("Keeping high-exp job '%s' — %d skill matches despite %d yr req", job.get('title'), skill_count, exp)
                return True
            else:
                logger.debug("Filtering out '%s' — requires %d yrs, only %d skill matches", job.get('title'), exp, skill_count)
                return False
        return True

    def _title_matches(self, title: str) -> bool:
        for role in self.target_titles:
            if role in title:
                return True
        partial_keywords = ['ai', 'ml', 'python', 'django', 'react', 'backend', 'fullstack', 'full stack', 'full-stack', 'sde', 'developer', 'engineer', 'software']
        for kw in partial_keywords:
            if kw in title:
                return True
        return False

    def _count_matching_skills(self, text: str) -> int:
        count = 0
        for skill in self.skills:
            if skill in text:
                count += 1
        return count

    def filter_jobs(self, jobs: list[dict]) -> list[dict]:
        kept = []
        filtered_count = 0
        for job in jobs:
            if self.should_keep(job):
                kept.append(job)
            else:
                filtered_count += 1
        logger.info('Filtering: %d kept, %d removed out of %d total', len(kept), filtered_count, len(jobs))
        return kept