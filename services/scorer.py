import config
from utils.logger import get_logger
logger = get_logger('scorer')

class JobScorer:

    def __init__(self):
        self.highest_roles = [r.lower() for r in config.TARGET_ROLES['highest']]
        self.secondary_roles = [r.lower() for r in config.TARGET_ROLES['secondary']]
        self.additional_roles = [r.lower() for r in config.TARGET_ROLES['additional']]
        self.ai_keywords = [k.lower() for k in config.AI_KEYWORDS]
        self.skills = [s.lower() for s in config.SKILLS]
        self.target_locations = [l.lower() for l in config.TARGET_LOCATIONS]

    def score(self, job: dict) -> int:
        score = 0
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        location = job.get('location', '').lower()
        full_text = f'{title} {description}'
        score += self._score_title(title)
        score += self._score_ai_keywords(full_text)
        score += self._score_skills(full_text)
        score += self._score_location(location)
        logger.debug("Scored job '%s' at %s → %d points", job.get('title'), job.get('company'), score)
        return score

    def _score_title(self, title: str) -> int:
        points = 0
        for role in self.highest_roles:
            if role in title:
                points += 100
                break
        if points == 0:
            for role in self.secondary_roles:
                if role in title:
                    points += 70
                    break
        if points == 0:
            for role in self.additional_roles:
                if role in title:
                    points += 50
                    break
        if points == 0:
            ai_title_keywords = ['ai', 'ml', 'machine learning', 'artificial intelligence', 'llm', 'genai']
            for kw in ai_title_keywords:
                if kw in title:
                    points += 40
                    break
            dev_title_keywords = ['developer', 'engineer', 'sde', 'programmer']
            for kw in dev_title_keywords:
                if kw in title and points == 0:
                    points += 30
                    break
        return points

    def _score_ai_keywords(self, text: str) -> int:
        points = 0
        matched = set()
        for keyword in self.ai_keywords:
            if keyword in text and keyword not in matched:
                points += 30
                matched.add(keyword)
        return min(points, 120)

    def _score_skills(self, text: str) -> int:
        points = 0
        matched = set()
        high_value = {'python': 20, 'django': 20, 'react': 15, 'typescript': 15, 'javascript': 10, 'aws': 10, 'docker': 10}
        standard_value = {'postgresql': 10, 'mongodb': 10, 'mysql': 10, 'rest api': 10, 'restful': 10, 'websocket': 10}
        for (skill, value) in high_value.items():
            if skill in text and skill not in matched:
                points += value
                matched.add(skill)
        for (skill, value) in standard_value.items():
            if skill in text and skill not in matched:
                points += value
                matched.add(skill)
        return points

    def _score_location(self, location: str) -> int:
        points = 0
        if not location:
            return 0
        remote_keywords = ['remote', 'work from home', 'wfh', 'anywhere']
        for kw in remote_keywords:
            if kw in location:
                points += 15
                break
        india_cities = ['bangalore', 'bengaluru', 'mumbai', 'delhi', 'ncr', 'hyderabad', 'pune', 'chennai', 'gurgaon', 'gurugram', 'noida', 'kolkata', 'india']
        for city in india_cities:
            if city in location:
                points += 5
                break
        return points

    def score_and_attach(self, jobs: list[dict]) -> list[dict]:
        for job in jobs:
            job['score'] = self.score(job)
        jobs.sort(key=lambda j: j['score'], reverse=True)
        return jobs