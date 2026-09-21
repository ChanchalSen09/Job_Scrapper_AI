"""
SQLite database layer with backward-compatible v2 schema migration.

Migration strategy: uses ALTER TABLE ADD COLUMN — safe on existing databases.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
import config
from database.models import CREATE_JOBS_TABLE, CREATE_INDEXES, V2_COLUMNS, Job
from utils.logger import get_logger
from utils.helpers import normalize_title

logger = get_logger('database')


class Database:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_db()

    # ─── Connection ────────────────────────────────────────────────────────

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA foreign_keys=ON;')
        return conn

    # ─── Initialization & Migration ────────────────────────────────────────

    def _init_db(self) -> None:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(CREATE_JOBS_TABLE)
            for index_sql in CREATE_INDEXES:
                cursor.execute(index_sql)
            conn.commit()
            # Run v2 migration (safe no-op if columns already exist)
            self._migrate_schema(conn)
            conn.close()
            logger.info('Database initialized at: %s', self.db_path)
        except sqlite3.Error as e:
            logger.error('Failed to initialize database: %s', e)
            raise

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        """
        Safely add v2 columns to an existing database.
        Uses ALTER TABLE ... ADD COLUMN which is a no-op if column already exists
        (handled by catching the OperationalError).
        """
        cursor = conn.cursor()
        # Get existing columns
        cursor.execute("PRAGMA table_info(jobs)")
        existing_cols = {row['name'] for row in cursor.fetchall()}

        added = []
        for col_name, col_def in V2_COLUMNS:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f'ALTER TABLE jobs ADD COLUMN {col_name} {col_def}')
                    added.append(col_name)
                except sqlite3.OperationalError as e:
                    # Column may already exist in a concurrent run
                    logger.debug('Column %s migration skipped: %s', col_name, e)
        conn.commit()
        if added:
            logger.info('Database migrated: added columns %s', added)

    # ─── Existence Check ───────────────────────────────────────────────────

    def job_exists(self, url: str, title: str = '', company: str = '') -> bool:
        """
        Deduplicate by:
        1. Exact normalized URL
        2. company + normalized title
        3. source + company + normalized title (handled by (2))
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if url:
                cursor.execute('SELECT 1 FROM jobs WHERE url = ? LIMIT 1', (url,))
                if cursor.fetchone() is not None:
                    conn.close()
                    return True

            if title and company:
                norm_title = normalize_title(title)
                cursor.execute(
                    'SELECT 1 FROM jobs WHERE LOWER(company) = ? AND LOWER(title) = ? LIMIT 1',
                    (company.lower(), norm_title),
                )
                if cursor.fetchone() is not None:
                    conn.close()
                    return True

            conn.close()
            return False
        except sqlite3.Error as e:
            logger.error('Error checking job existence: %s', e)
            return False

    # ─── Insert ────────────────────────────────────────────────────────────

    def insert_job(self, job: dict) -> bool:
        """Insert a new job with all v2 scoring fields."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT OR IGNORE INTO jobs (
                    title, company, location, url, source, description,
                    score, notified,
                    final_score, role_category, ai_score, backend_score,
                    experience_match, location_score, freshness_score,
                    matched_skills, missing_required_skills, match_reason,
                    rejection_reason, experience_requirement, work_type, posted_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    job.get('title', ''),
                    job.get('company', ''),
                    job.get('location', ''),
                    job.get('url', ''),
                    job.get('source', ''),
                    job.get('description', ''),
                    job.get('final_score', job.get('score', 0)),  # v1 compat
                    job.get('final_score', 0),
                    job.get('role_category', ''),
                    job.get('ai_score', 0),
                    job.get('backend_score', 0),
                    _serialize_exp(job.get('experience_requirement', {})),
                    job.get('location_score', 0),
                    job.get('freshness_score', 0),
                    _serialize_list(job.get('matched_skills', [])),
                    _serialize_list(job.get('missing_required_skills', [])),
                    job.get('match_reason', ''),
                    job.get('rejection_reason', ''),
                    _serialize_exp(job.get('experience_requirement', {})),
                    job.get('work_type', ''),
                    job.get('posted_date', ''),
                ),
            )
            inserted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            if inserted:
                logger.debug(
                    'Inserted: [%s] %s @ %s (score=%d, band=%s)',
                    job.get('source', ''),
                    job.get('title', ''),
                    job.get('company', ''),
                    job.get('final_score', 0),
                    job.get('match_band', ''),
                )
            return inserted
        except sqlite3.Error as e:
            logger.error('Error inserting job: %s', e)
            return False

    def insert_jobs_batch(self, jobs: list[dict]) -> int:
        """Batch insert — returns count of newly inserted jobs."""
        inserted_count = 0
        for job in jobs:
            if self.insert_job(job):
                inserted_count += 1
        logger.info('Batch insert: %d new jobs out of %d total', inserted_count, len(jobs))
        return inserted_count

    # ─── Queries ───────────────────────────────────────────────────────────

    def get_unnotified_jobs(self) -> list[dict]:
        """Return unnotified jobs, sorted best-score-first."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT * FROM jobs
                WHERE notified = 0
                ORDER BY final_score DESC, created_at DESC
                '''
            )
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
            cursor.execute(
                "DELETE FROM jobs WHERE created_at <= datetime('now', ?)",
                (f'-{retention_days} days',),
            )
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            if deleted_count > 0:
                logger.info('Cleaned up %d old jobs (>%d days)', deleted_count, retention_days)
            return deleted_count
        except sqlite3.Error as e:
            logger.error('Error cleaning up old jobs: %s', e)
            return 0

    def get_stats(self) -> dict:
        """Return pipeline statistics including v2 fields."""
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

            cursor.execute('SELECT AVG(final_score) FROM jobs WHERE final_score > 0')
            avg_raw = cursor.fetchone()[0]
            avg_score = round(avg_raw, 1) if avg_raw else 0.0

            cursor.execute(
                '''
                SELECT role_category, COUNT(*) as count
                FROM jobs
                WHERE role_category != '' AND DATE(created_at) = ?
                GROUP BY role_category
                ORDER BY count DESC
                ''',
                (today,),
            )
            by_role = {row['role_category']: row['count'] for row in cursor.fetchall()}

            # Band breakdown today
            cursor.execute(
                '''
                SELECT
                    SUM(CASE WHEN final_score >= 90 THEN 1 ELSE 0 END) as excellent,
                    SUM(CASE WHEN final_score >= 80 AND final_score < 90 THEN 1 ELSE 0 END) as strong,
                    SUM(CASE WHEN final_score >= 70 AND final_score < 80 THEN 1 ELSE 0 END) as good,
                    SUM(CASE WHEN final_score >= 60 AND final_score < 70 THEN 1 ELSE 0 END) as borderline,
                    SUM(CASE WHEN final_score < 60 THEN 1 ELSE 0 END) as skip
                FROM jobs WHERE DATE(created_at) = ?
                ''',
                (today,),
            )
            row = cursor.fetchone()
            bands_today = {
                'EXCELLENT': row['excellent'] or 0,
                'STRONG': row['strong'] or 0,
                'GOOD': row['good'] or 0,
                'BORDERLINE': row['borderline'] or 0,
                'SKIP': row['skip'] or 0,
            } if row else {}

            conn.close()
            return {
                'total': total,
                'today': today_count,
                'by_source': by_source,
                'unnotified': unnotified,
                'avg_score': avg_score,
                'by_role': by_role,
                'bands_today': bands_today,
            }
        except sqlite3.Error as e:
            logger.error('Error fetching stats: %s', e)
            return {'total': 0, 'today': 0, 'by_source': {}, 'unnotified': 0, 'avg_score': 0}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _serialize_list(value) -> str:
    """Serialize list to JSON string for storage."""
    if isinstance(value, list):
        return json.dumps(value)
    if isinstance(value, str):
        return value
    return ''


def _serialize_exp(value) -> str:
    """Serialize experience_requirement dict to JSON string."""
    if isinstance(value, dict):
        return json.dumps(value)
    if isinstance(value, str):
        return value
    return ''