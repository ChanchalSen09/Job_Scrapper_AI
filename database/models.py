"""
Database models and schema for the job scraper.

New columns added in v2 (backward-compatible via ALTER TABLE migration):
  final_score, role_category, ai_score, backend_score, experience_match,
  location_score, freshness_score, matched_skills, missing_required_skills,
  match_reason, rejection_reason, experience_requirement, work_type, posted_date
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# DDL
# ─────────────────────────────────────────────────────────────────────────────

CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT DEFAULT '',
    url TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    description TEXT DEFAULT '',
    -- v1 score (kept for backward compat; equals final_score in v2)
    score INTEGER DEFAULT 0,
    notified INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- v2 scoring fields
    final_score INTEGER DEFAULT 0,
    role_category TEXT DEFAULT '',
    ai_score INTEGER DEFAULT 0,
    backend_score INTEGER DEFAULT 0,
    experience_match TEXT DEFAULT '',
    location_score INTEGER DEFAULT 0,
    freshness_score INTEGER DEFAULT 0,
    matched_skills TEXT DEFAULT '',
    missing_required_skills TEXT DEFAULT '',
    match_reason TEXT DEFAULT '',
    rejection_reason TEXT DEFAULT '',
    experience_requirement TEXT DEFAULT '',
    work_type TEXT DEFAULT '',
    posted_date TEXT DEFAULT ''
);
"""

# Indexes
CREATE_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);',
    'CREATE INDEX IF NOT EXISTS idx_jobs_final_score ON jobs(final_score DESC);',
    'CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);',
    'CREATE INDEX IF NOT EXISTS idx_jobs_notified ON jobs(notified);',
    'CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);',
    'CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);',
    'CREATE INDEX IF NOT EXISTS idx_jobs_role_category ON jobs(role_category);',
    'CREATE INDEX IF NOT EXISTS idx_jobs_match_band ON jobs(final_score, notified);',
]

# Columns added in v2 — used for safe ALTER TABLE migration
V2_COLUMNS: list[tuple[str, str]] = [
    ('final_score', 'INTEGER DEFAULT 0'),
    ('role_category', 'TEXT DEFAULT \'\''),
    ('ai_score', 'INTEGER DEFAULT 0'),
    ('backend_score', 'INTEGER DEFAULT 0'),
    ('experience_match', 'TEXT DEFAULT \'\''),
    ('location_score', 'INTEGER DEFAULT 0'),
    ('freshness_score', 'INTEGER DEFAULT 0'),
    ('matched_skills', 'TEXT DEFAULT \'\''),
    ('missing_required_skills', 'TEXT DEFAULT \'\''),
    ('match_reason', 'TEXT DEFAULT \'\''),
    ('rejection_reason', 'TEXT DEFAULT \'\''),
    ('experience_requirement', 'TEXT DEFAULT \'\''),
    ('work_type', 'TEXT DEFAULT \'\''),
    ('posted_date', 'TEXT DEFAULT \'\''),
]


# ─────────────────────────────────────────────────────────────────────────────
# JOB DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Job:
    title: str
    company: str
    location: str = ''
    url: str = ''
    source: str = ''
    description: str = ''
    score: int = 0                      # backward compat == final_score
    notified: bool = False
    created_at: Optional[datetime] = field(default=None)
    id: Optional[int] = field(default=None)

    # v2 fields
    final_score: int = 0
    role_category: str = ''
    ai_score: int = 0
    backend_score: int = 0
    experience_match: str = ''
    location_score: int = 0
    freshness_score: int = 0
    matched_skills: str = ''             # JSON array string
    missing_required_skills: str = ''   # JSON array string
    match_reason: str = ''
    rejection_reason: str = ''
    experience_requirement: str = ''    # JSON object string
    work_type: str = ''
    posted_date: str = ''

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'url': self.url,
            'source': self.source,
            'description': self.description,
            'score': self.score,
            'notified': 1 if self.notified else 0,
            'final_score': self.final_score,
            'role_category': self.role_category,
            'ai_score': self.ai_score,
            'backend_score': self.backend_score,
            'experience_match': self.experience_match,
            'location_score': self.location_score,
            'freshness_score': self.freshness_score,
            'matched_skills': self.matched_skills,
            'missing_required_skills': self.missing_required_skills,
            'match_reason': self.match_reason,
            'rejection_reason': self.rejection_reason,
            'experience_requirement': self.experience_requirement,
            'work_type': self.work_type,
            'posted_date': self.posted_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Job':
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            company=data.get('company', ''),
            location=data.get('location', ''),
            url=data.get('url', ''),
            source=data.get('source', ''),
            description=data.get('description', ''),
            score=data.get('score', 0),
            notified=bool(data.get('notified', False)),
            created_at=data.get('created_at'),
            final_score=data.get('final_score', 0),
            role_category=data.get('role_category', ''),
            ai_score=data.get('ai_score', 0),
            backend_score=data.get('backend_score', 0),
            experience_match=data.get('experience_match', ''),
            location_score=data.get('location_score', 0),
            freshness_score=data.get('freshness_score', 0),
            matched_skills=data.get('matched_skills', ''),
            missing_required_skills=data.get('missing_required_skills', ''),
            match_reason=data.get('match_reason', ''),
            rejection_reason=data.get('rejection_reason', ''),
            experience_requirement=data.get('experience_requirement', ''),
            work_type=data.get('work_type', ''),
            posted_date=data.get('posted_date', ''),
        )

    @classmethod
    def from_row(cls, row: tuple, columns: list[str]) -> 'Job':
        data = dict(zip(columns, row))
        return cls.from_dict(data)