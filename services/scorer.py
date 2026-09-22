"""
Profile-driven job scorer for Chanchal Sen.

Scoring philosophy:
  "Would this job realistically make sense for Chanchal Sen to apply for?"

Final score: 0–100 normalized integer.
Scoring dimensions and weights come from config.SCORING_WEIGHTS.
"""

import re
from typing import Optional
import config
from utils.logger import get_logger
from utils.helpers import parse_experience_requirement, normalize_title

logger = get_logger('scorer')


# ─────────────────────────────────────────────────────────────────────────────
# ROLE CATEGORY CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

def _classify_role(title: str) -> str:
    """Map a job title to a role category string."""
    t = title.lower()
    # Check specific patterns first (most specific to least)
    for category, patterns in config.ROLE_CATEGORIES.items():
        for pattern in patterns:
            if pattern in t:
                return category
    # Fallback keyword checks — ORDER MATTERS: most specific first
    if any(kw in t for kw in ['agentic ai', 'agentic']):
        return 'AGENTIC_AI'
    if any(kw in t for kw in ['rag engineer', 'rag']):
        return 'RAG'
    if any(kw in t for kw in ['llm engineer', 'llm']):
        return 'LLM'
    if any(kw in t for kw in ['genai', 'generative ai']):
        return 'GENAI'
    if any(kw in t for kw in ['ai engineer', 'ai software', 'ai backend', 'ai']):
        return 'AI_CORE'
    if 'machine learning' in t or 'ml engineer' in t:
        return 'ML_APPLIED'
    if 'backend' in t or 'python' in t:
        return 'PYTHON_BACKEND'
    if 'full stack' in t or 'fullstack' in t:
        return 'FULL_STACK'
    if any(kw in t for kw in ['engineer', 'developer', 'sde']):
        return 'GENERIC_BACKEND'
    return 'LOW_MATCH'


# ─────────────────────────────────────────────────────────────────────────────
# HARD REJECTION
# ─────────────────────────────────────────────────────────────────────────────

def check_hard_rejections(job: dict) -> tuple[bool, str]:
    """
    Apply hard rejection rules.

    Returns (is_rejected: bool, reason: str).
    """
    title = job.get('title', '').lower()
    description = job.get('description', '').lower()
    company = job.get('company', '').lower()
    location = job.get('location', '').lower()
    full_text = f'{title} {description}'

    # ── Banned companies
    for banned in config.BANNED_COMPANIES:
        if banned.lower() in company:
            return True, f'Banned company: {company}'

    # ── Senior / leadership titles (must check title specifically)
    for kw in config.EXCLUDED_TITLE_KEYWORDS:
        if kw in title:
            return True, f'Senior/leadership role: "{kw}" in title'

    # ── Completely unrelated role types
    for role in config.EXCLUDED_ROLE_TYPES:
        if role in title:
            return True, f'Excluded role type: {role}'

    # ── Unrelated stacks in title
    for stack in config.EXCLUDED_STACKS:
        if stack in title:
            return True, f'Excluded tech stack: {stack}'

    # ── Experience hard rejection — parse from full_text
    exp = parse_experience_requirement(full_text)
    if exp.get('is_required') and exp.get('min') is not None:
        min_exp = exp['min']
        if min_exp >= config.EXPERIENCE_HARD_REJECT_MIN:
            return True, f'Experience requirement too high: {min_exp}+ years required'

    # ── Research-heavy ML (not application-focused)
    research_signals = [
        'pytorch research', 'tensorflow research', 'model training',
        'deep learning research', 'nlp research', 'computer vision research',
        'model architecture', 'phd', 'research engineer', 'research scientist',
        'ml researcher',
    ]
    research_count = sum(1 for sig in research_signals if sig in full_text)
    if research_count >= 2 and 'application' not in full_text and 'api' not in full_text:
        return True, f'ML research role (signals: {research_count}), not application-focused'

    # ── Internship-only / unpaid
    internship_patterns = [
        r'\bunpaid\s+intern\b',
        r'\binternship\s+only\b',
        r'\bstipend\s+(?:only|based)\b',
    ]
    for p in internship_patterns:
        if re.search(p, full_text):
            return True, 'Unpaid or internship-only role'

    return False, ''


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCORER
# ─────────────────────────────────────────────────────────────────────────────

class JobScorer:

    def __init__(self):
        # Pre-compile keyword lists for speed
        self._all_roles = {}
        for category, roles in config.TARGET_ROLES.items():
            pts = config.TARGET_ROLE_SCORES.get(category, 60)
            for role in roles:
                self._all_roles[role.lower()] = pts
        # sort by points descending
        self._all_roles = dict(sorted(self._all_roles.items(), key=lambda item: item[1], reverse=True))
        self._ai_keywords = {k.lower(): v for k, v in config.AI_KEYWORDS.items()}
        self._backend_skills = {k.lower(): v for k, v in config.BACKEND_SKILLS.items()}
        self._frontend_skills = {k.lower(): v for k, v in config.FRONTEND_SKILLS.items()}
        self._cloud_skills = {k.lower(): v for k, v in config.CLOUD_SKILLS.items()}
        self._responsibility_kws = {k.lower(): v for k, v in config.RESPONSIBILITY_KEYWORDS.items()}
        self._fullstack_titles = [t.lower() for t in config.FULLSTACK_AI_TITLES]

    # ─── Public API ────────────────────────────────────────────────────────

    def score_and_explain(self, job: dict) -> dict:
        """
        Score a job and return a complete explanation dict.

        Attaches all sub-scores, match band, role category, and human-readable
        match_reason or rejection_reason.
        """
        # Hard rejection check first
        is_rejected, rejection_reason = check_hard_rejections(job)
        if is_rejected:
            return self._rejected_result(job, rejection_reason)

        title = job.get('title', '').title()
        location = job.get('location', '').lower()
        description = job.get('description', '').lower()
        full_text = f'{title.lower()} {description}'
        
        from utils.helpers import extract_work_type
        work_type = extract_work_type(f'{location} {full_text[:200]}')
        
        exp_req = parse_experience_requirement(full_text)
        lo = exp_req.get('min')
        hi = exp_req.get('max')
        if exp_req.get('freshers_welcome'):
            exp_str = 'Freshers welcome'
        elif lo is not None and hi is not None and lo != hi:
            exp_str = f'{lo}–{hi} years'
        elif lo is not None and exp_req.get('is_plus'):
            exp_str = f'{lo}+ years'
        elif lo is not None:
            exp_str = f'{lo} years'
        else:
            exp_str = 'Not specified'

        return {
            'final_score': 100,
            'match_band': 'EXCELLENT',
            'role_category': 'MATCHED',
            'role_score': 100,
            'ai_score': 0,
            'backend_score': 0,
            'frontend_score': 0,
            'cloud_score': 0,
            'responsibility_score': 0,
            'experience_score': 0,
            'location_score': 0,
            'matched_skills': [],
            'missing_required_skills': [],
            'matched_role': title,
            'experience_requirement': exp_req,
            'match_reason': f"Found Job | Exp: {exp_str} | {work_type.capitalize()}",
            'rejection_reason': None,
            'is_rejected': False,
            'work_type': work_type,
        }

    def score_and_attach(self, jobs: list[dict]) -> list[dict]:
        """Score all jobs, attach result fields, sort by final_score desc."""
        for job in jobs:
            result = self.score_and_explain(job)
            job.update(result)
            # Also maintain backward-compat 'score' key
            job['score'] = result['final_score']
        jobs.sort(key=lambda j: j.get('final_score', 0), reverse=True)
        return jobs

    # ─── Dimension scorers ─────────────────────────────────────────────────

    def _score_role_match(self, title: str) -> tuple[int, str, str]:
        """
        Returns (raw_points, matched_role_name, role_category).
        Raw scale: 0–120.
        """
        for role, pts in self._all_roles.items():
            if role in title:
                return pts, role, _classify_role(title)
        # Fallback: AI keyword in title
        ai_title_kws = ['ai', 'genai', 'llm', 'rag', 'agentic', 'generative']
        for kw in ai_title_kws:
            if re.search(r'\b' + kw + r'\b', title):
                return 120, kw, 'AI_CORE'
        dev_kws = ['developer', 'engineer', 'sde', 'programmer']
        for kw in dev_kws:
            if kw in title:
                return 120, kw, 'GENERIC_BACKEND'
        return 0, '', 'LOW_MATCH'

    def _score_ai_relevance(self, text: str) -> tuple[int, set]:
        """
        Returns (raw_points capped at AI_SCORE_CAP, set of matched keywords).
        """
        points = 0
        matched = set()
        for kw, pts in self._ai_keywords.items():
            if kw in text and kw not in matched:
                points += pts
                matched.add(kw)
                if points >= config.AI_SCORE_CAP:
                    break
        return min(points, config.AI_SCORE_CAP), matched

    def _score_backend_alignment(self, text: str) -> tuple[int, list]:
        """Returns (raw_points capped at BACKEND_SCORE_CAP, matched skills list)."""
        points = 0
        matched = []
        for skill, pts in self._backend_skills.items():
            if skill in text and skill not in matched:
                points += pts
                matched.append(skill)
        return min(points, config.BACKEND_SCORE_CAP), matched

    def _score_frontend_alignment(self, title: str, text: str) -> tuple[int, list]:
        """
        Only applies meaningful weight for full-stack/AI-app titles.
        Returns (raw_points capped at FRONTEND_SCORE_CAP, matched skills list).
        """
        is_fullstack = any(t in title for t in self._fullstack_titles)
        if not is_fullstack:
            # Minor bonus only — still count but cap low
            cap = 15
        else:
            cap = config.FRONTEND_SCORE_CAP
        points = 0
        matched = []
        for skill, pts in self._frontend_skills.items():
            if skill in text and skill not in matched:
                points += pts
                matched.append(skill)
        return min(points, cap), matched

    def _score_cloud_devops(self, text: str) -> tuple[int, list]:
        """Returns (raw_points capped at CLOUD_SCORE_CAP, matched skills list)."""
        points = 0
        matched = []
        for skill, pts in self._cloud_skills.items():
            if skill in text and skill not in matched:
                points += pts
                matched.append(skill)
        return min(points, config.CLOUD_SCORE_CAP), matched

    def _score_responsibilities(self, text: str) -> int:
        """Returns raw responsibility keyword score capped at RESPONSIBILITY_SCORE_CAP."""
        points = 0
        matched = set()
        for kw, pts in self._responsibility_kws.items():
            if kw in text and kw not in matched:
                points += pts
                matched.add(kw)
        return min(points, config.RESPONSIBILITY_SCORE_CAP)

    def _score_experience(self, text: str) -> tuple[int, dict]:
        """
        Returns (score 0–100, exp_requirement dict).

        Score mapping:
          freshers_welcome / 0-1 yr  → 100
          1-2 years                  → 95
          1-3 years                  → 90
          2-3 years                  → 80
          2+ years (preferred)       → 70
          2+ years (required)        → 65
          exactly 3 years            → 60
          3+ preferred               → 40
          3+ required                → 0 (effectively soft-rejected via score)
          4+ required                → 0
          unknown                    → 60 (neutral)
        """
        exp = parse_experience_requirement(text)

        if exp.get('freshers_welcome'):
            return 100, exp

        lo = exp.get('min')
        hi = exp.get('max')
        is_plus = exp.get('is_plus', False)
        is_preferred = exp.get('is_preferred', False)
        is_required = exp.get('is_required', False)

        if lo is None and hi is None:
            return 70, exp  # Unknown — slightly positive (no restriction is good)

        # Range cases
        if exp.get('is_range') and lo is not None and hi is not None:
            if hi <= 1:
                return 100, exp
            if hi == 2:
                return 95, exp
            if hi == 3 and lo <= 1:
                return 90, exp
            if hi == 3 and lo == 2:
                return 80, exp
            if hi == 3:
                return 70, exp
            if hi == 4 and lo <= 2:
                return 55, exp
            if hi >= 5:
                return 10, exp
            return 50, exp

        # Plus/minimum cases
        if lo is not None:
            if lo <= 1:
                return 90, exp
            if lo == 2 and is_preferred:
                return 70, exp
            if lo == 2 and is_required:
                return 65, exp
            if lo == 2:
                return 65, exp
            if lo == 3 and is_preferred:
                return 40, exp
            if lo == 3:
                return 20, exp
            if lo >= 4:
                return 0, exp

        return 60, exp  # Fallback neutral

    def _score_location(self, location: str, full_text: str) -> tuple[int, str]:
        """
        Returns (raw_points 0–30, work_type string).
        """
        from utils.helpers import extract_work_type
        work_type = extract_work_type(f'{location} {full_text[:200]}')

        if work_type == 'remote':
            return 30, work_type
        if work_type == 'hybrid':
            # Check if India
            if any(city in location.lower() for city in config.TIER_1_CITIES + ['india']):
                return 20, work_type
            return 10, work_type
        if work_type == 'onsite':
            if any(city in location.lower() for city in config.TIER_1_CITIES):
                return 15, work_type
            if any(city in location.lower() for city in config.TIER_2_CITIES):
                return 10, work_type
            if 'india' in location.lower():
                return 8, work_type
            return 0, work_type
        # Unknown
        if 'india' in location.lower():
            return 5, work_type
        return 0, work_type

    # ─── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _norm(raw: int, max_raw: int) -> float:
        """Normalize raw score to 0–100 float."""
        if max_raw <= 0:
            return 0.0
        return min(100.0, (raw / max_raw) * 100)

    def _build_match_reason(
        self,
        matched_role: str,
        role_cat: str,
        matched_skills: list,
        exp_req: dict,
        location: str,
        work_type: str,
        final: int,
        match_band: str,
    ) -> str:
        """Generate a concise human-readable match explanation."""
        parts = []

        # Role descriptor
        if matched_role:
            parts.append(f'{match_band} match: {matched_role.title()}')
        else:
            parts.append(f'{match_band} match')

        # Top matched skills (max 6)
        top_skills = matched_skills[:6]
        if top_skills:
            parts.append(' + '.join(s.title() for s in top_skills))

        # Experience
        lo = exp_req.get('min')
        hi = exp_req.get('max')
        if exp_req.get('freshers_welcome'):
            parts.append('Experience: Freshers welcome')
        elif lo is not None and hi is not None and lo != hi:
            parts.append(f'Experience: {lo}–{hi} years')
        elif lo is not None and exp_req.get('is_plus'):
            parts.append(f'Experience: {lo}+ years')
        elif lo is not None:
            parts.append(f'Experience: {lo} years')
        else:
            parts.append('Experience: Not specified')

        # Location
        loc_display = work_type.capitalize() if work_type != 'unknown' else location[:40]
        parts.append(f'Location: {loc_display}')

        return ' | '.join(parts)

    def _rejected_result(self, job: dict, reason: str) -> dict:
        """Return a standardized rejection result dict."""
        return {
            'final_score': 0,
            'match_band': 'REJECTED',
            'role_category': 'REJECTED',
            'role_score': 0,
            'ai_score': 0,
            'backend_score': 0,
            'frontend_score': 0,
            'cloud_score': 0,
            'responsibility_score': 0,
            'experience_score': 0,
            'location_score': 0,
            'matched_skills': [],
            'missing_required_skills': [],
            'matched_role': '',
            'experience_requirement': {},
            'match_reason': '',
            'rejection_reason': reason,
            'is_rejected': True,
            'work_type': 'unknown',
            'score': 0,  # backward compat
        }


# ─────────────────────────────────────────────────────────────────────────────
# BAND UTILITY
# ─────────────────────────────────────────────────────────────────────────────

def _get_band(score: int) -> str:
    if score >= config.MATCH_BANDS['EXCELLENT']:
        return 'EXCELLENT'
    if score >= config.MATCH_BANDS['STRONG']:
        return 'STRONG'
    if score >= config.MATCH_BANDS['GOOD']:
        return 'GOOD'
    if score >= config.MATCH_BANDS['BORDERLINE']:
        return 'BORDERLINE'
    return 'SKIP'