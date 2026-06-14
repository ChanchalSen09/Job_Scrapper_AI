from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
CREATE_JOBS_TABLE = "\nCREATE TABLE IF NOT EXISTS jobs (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    title TEXT NOT NULL,\n    company TEXT NOT NULL,\n    location TEXT DEFAULT '',\n    url TEXT UNIQUE NOT NULL,\n    source TEXT NOT NULL,\n    description TEXT DEFAULT '',\n    score INTEGER DEFAULT 0,\n    notified INTEGER DEFAULT 0,\n    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n"
CREATE_INDEXES = ['CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);', 'CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);', 'CREATE INDEX IF NOT EXISTS idx_jobs_notified ON jobs(notified);', 'CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);', 'CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);']

@dataclass
class Job:
    title: str
    company: str
    location: str = ''
    url: str = ''
    source: str = ''
    description: str = ''
    score: int = 0
    notified: bool = False
    created_at: Optional[datetime] = field(default=None)
    id: Optional[int] = field(default=None)

    def to_dict(self) -> dict:
        return {'title': self.title, 'company': self.company, 'location': self.location, 'url': self.url, 'source': self.source, 'description': self.description, 'score': self.score, 'notified': 1 if self.notified else 0}

    @classmethod
    def from_dict(cls, data: dict) -> 'Job':
        return cls(id=data.get('id'), title=data.get('title', ''), company=data.get('company', ''), location=data.get('location', ''), url=data.get('url', ''), source=data.get('source', ''), description=data.get('description', ''), score=data.get('score', 0), notified=bool(data.get('notified', False)), created_at=data.get('created_at'))

    @classmethod
    def from_row(cls, row: tuple, columns: list[str]) -> 'Job':
        data = dict(zip(columns, row))
        return cls.from_dict(data)