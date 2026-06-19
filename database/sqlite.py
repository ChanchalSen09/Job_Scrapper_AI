import sqlite3
from datetime import datetime, timedelta
from typing import Optional
import config
from database.models import CREATE_JOBS_TABLE, CREATE_INDEXES, Job
from utils.logger import get_logger
logger = get_logger('database')

class Database:

    def __init__(self, db_path: Optional[str]=None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA foreign_keys=ON;')
        return conn

    def _init_db(self) -> None:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(CREATE_JOBS_TABLE)
            for index_sql in CREATE_INDEXES:
                cursor.execute(index_sql)
            conn.commit()
            conn.close()
            logger.info('Database initialized successfully at: %s', self.db_path)
        except sqlite3.Error as e:
            logger.error('Failed to initialize database: %s', e)
            raise

    def job_exists(self, url: str, title: str = "", company: str = "") -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if url:
                cursor.execute('SELECT 1 FROM jobs WHERE url = ? LIMIT 1', (url,))
                if cursor.fetchone() is not None:
                    conn.close()
                    return True
            
            if title and company:
                cursor.execute('SELECT 1 FROM jobs WHERE LOWER(title) = ? AND LOWER(company) = ? LIMIT 1', (title.lower(), company.lower()))
                if cursor.fetchone() is not None:
                    conn.close()
                    return True

            conn.close()
            return False
        except sqlite3.Error as e:
            logger.error('Error checking job existence: %s', e)
            return False

    def insert_job(self, job: dict) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('\n                INSERT OR IGNORE INTO jobs (title, company, location, url, source, description, score, notified)\n                VALUES (?, ?, ?, ?, ?, ?, ?, 0)\n                ', (job.get('title', ''), job.get('company', ''), job.get('location', ''), job.get('url', ''), job.get('source', ''), job.get('description', ''), job.get('score', 0)))
            inserted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            if inserted:
                logger.debug('Inserted new job: %s at %s', job.get('title'), job.get('company'))
            return inserted
        except sqlite3.Error as e:
            logger.error('Error inserting job: %s', e)
            return False

    def insert_jobs_batch(self, jobs: list[dict]) -> int:
        inserted_count = 0
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            for job in jobs:
                cursor.execute('\n                    INSERT OR IGNORE INTO jobs (title, company, location, url, source, description, score, notified)\n                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)\n                    ', (job.get('title', ''), job.get('company', ''), job.get('location', ''), job.get('url', ''), job.get('source', ''), job.get('description', ''), job.get('score', 0)))
                if cursor.rowcount > 0:
                    inserted_count += 1
            conn.commit()
            conn.close()
            logger.info('Batch insert: %d new jobs out of %d total', inserted_count, len(jobs))
            return inserted_count
        except sqlite3.Error as e:
            logger.error('Error in batch insert: %s', e)
            return inserted_count

    def get_unnotified_jobs(self) -> list[dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('\n                SELECT id, title, company, location, url, source, description, score, notified, created_at\n                FROM jobs\n                WHERE notified = 0\n                ORDER BY score DESC, created_at DESC\n                ')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error('Error fetching unnotified jobs: %s', e)
            return []

    def mark_notified(self, job_ids: list[int]) -> None:
        if not job_ids:
            return
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in job_ids])
            cursor.execute(f'UPDATE jobs SET notified = 1 WHERE id IN ({placeholders})', job_ids)
            conn.commit()
            conn.close()
            logger.info('Marked %d jobs as notified', len(job_ids))
        except sqlite3.Error as e:
            logger.error('Error marking jobs as notified: %s', e)

    def cleanup_old_jobs(self, retention_days: int) -> int:
        if retention_days <= 0:
            return 0
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE created_at <= datetime('now', ?)", (f'-{retention_days} days',))
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            if deleted_count > 0:
                logger.info('🧹 Cleaned up %d old jobs (older than %d days)', deleted_count, retention_days)
            return deleted_count
        except sqlite3.Error as e:
            logger.error('Error cleaning up old jobs: %s', e)
            return 0

    def get_stats(self) -> dict:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM jobs')
            total = cursor.fetchone()[0]
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('SELECT COUNT(*) FROM jobs WHERE DATE(created_at) = ?', (today,))
            today_count = cursor.fetchone()[0]
            cursor.execute('SELECT source, COUNT(*) as count FROM jobs GROUP BY source ORDER BY count DESC')
            by_source = {row['source']: row['count'] for row in cursor.fetchall()}
            cursor.execute('SELECT COUNT(*) FROM jobs WHERE notified = 0')
            unnotified = cursor.fetchone()[0]
            cursor.execute('SELECT AVG(score) FROM jobs')
            avg_score_raw = cursor.fetchone()[0]
            avg_score = round(avg_score_raw, 1) if avg_score_raw else 0
            conn.close()
            return {'total': total, 'today': today_count, 'by_source': by_source, 'unnotified': unnotified, 'avg_score': avg_score}
        except sqlite3.Error as e:
            logger.error('Error fetching stats: %s', e)
            return {'total': 0, 'today': 0, 'by_source': {}, 'unnotified': 0, 'avg_score': 0}