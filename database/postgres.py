"""
PostgreSQL database layer with backward-compatible v2 schema migration.

Migration strategy: uses ALTER TABLE ADD COLUMN — safe on existing databases.
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Optional
import config
from database.models import CREATE_JOBS_TABLE, CREATE_INDEXES, V2_COLUMNS, Job
from utils.logger import get_logger
from utils.helpers import normalize_title

logger = get_logger('database')


class Database:

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or config.DATABASE_URL
        if not self.db_url:
            logger.error("DATABASE_URL is not set in environment or config.")
            raise ValueError("DATABASE_URL is required for PostgreSQL.")
        self._init_db()

    # ─── Connection ────────────────────────────────────────────────────────

    def _get_connection(self):
        conn = psycopg2.connect(self.db_url)
        # Use RealDictCursor to act like sqlite3.Row
        return conn

    def _get_cursor(self, conn):
        return conn.cursor(cursor_factory=RealDictCursor)

    # ─── Initialization & Migration ────────────────────────────────────────

    def _init_db(self) -> None:
        try:
            conn = self._get_connection()
            cursor = self._get_cursor(conn)
            cursor.execute(CREATE_JOBS_TABLE)
            conn.commit()
            
            # Run v2 migration (safe no-op if columns already exist) BEFORE creating indexes
            self._migrate_schema(conn)
            
            for index_sql in CREATE_INDEXES:
                cursor.execute(index_sql)
            conn.commit()
            conn.close()
            logger.info('Database initialized on PostgreSQL')
        except psycopg2.Error as e:
            logger.error('Failed to initialize database: %s', e)
            raise

    def _migrate_schema(self, conn) -> None:
        """
        Safely add v2 columns to an existing database.
        Uses ALTER TABLE ... ADD COLUMN IF NOT EXISTS in PostgreSQL where possible,
        or just catch DuplicateColumn error.
        """
        cursor = self._get_cursor(conn)
        # Get existing columns
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='scraped_jobs'")
        existing_cols = {row['column_name'] for row in cursor.fetchall()}

        added = []
        for col_name, col_def in V2_COLUMNS:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f'ALTER TABLE scraped_jobs ADD COLUMN IF NOT EXISTS {col_name} {col_def}')
                    added.append(col_name)
                except psycopg2.errors.DuplicateColumn as e:
                    # Column may already exist in a concurrent run
                    conn.rollback() # must rollback to continue
                    logger.debug('Column %s migration skipped: %s', col_name, e)
                except Exception as e:
                    conn.rollback()
                    logger.debug('Error adding column %s: %s', col_name, e)
        conn.commit()
        if added:
            logger.info('Database migrated: added columns %s', added)

    # ─── Existence Check ───────────────────────────────────────────────────

    def job_exists(self, url: str, title: str = '', company: str = '') -> bool:
        """
        Deduplicate by:
        1. Exact normalized URL
        2. company + normalized title
        """
        try:
            conn = self._get_connection()
            cursor = self._get_cursor(conn)

            if url:
                cursor.execute('SELECT 1 FROM scraped_jobs WHERE url = %s LIMIT 1', (url,))
                if cursor.fetchone() is not None:
                    conn.close()
                    return True

            if title and company:
                norm_title = normalize_title(title)
                cursor.execute(
                    'SELECT 1 FROM scraped_jobs WHERE LOWER(company) = %s AND LOWER(title) = %s LIMIT 1',
                    (company.lower(), norm_title),
                )
                if cursor.fetchone() is not None:
                    conn.close()
                    return True

            conn.close()
            return False
        except psycopg2.Error as e:
            logger.error('Error checking job existence: %s', e)
            return False

    # ─── Insert ────────────────────────────────────────────────────────────

    def insert_job(self, job: dict) -> bool:
        """Insert a new job with all v2 scoring fields."""
        try:
            conn = self._get_connection()
            cursor = self._get_cursor(conn)
            cursor.execute(
                '''
                INSERT INTO scraped_jobs (
                    title, company, location, url, source, description,
                    score, notified,
                    final_score, role_category, ai_score, backend_score,
                    experience_match, location_score, freshness_score,
                    matched_skills, missing_required_skills, match_reason,
                    rejection_reason, experience_requirement, work_type, posted_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
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
        except psycopg2.Error as e:
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
            cursor = self._get_cursor(conn)
            cursor.execute(
                '''
                SELECT * FROM scraped_jobs
                WHERE notified = 0
                ORDER BY final_score DESC, created_at DESC
                '''
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except psycopg2.Error as e:
            logger.error('Error fetching unnotified jobs: %s', e)
            return []

    def mark_notified(self, job_ids: list[int]) -> None:
        if not job_ids:
            return
        try:
            conn = self._get_connection()
            cursor = self._get_cursor(conn)
            placeholders = ','.join(['%s' for _ in job_ids])
            cursor.execute(f'UPDATE scraped_jobs SET notified = 1 WHERE id IN ({placeholders})', job_ids)
            conn.commit()
            conn.close()
            logger.info('Marked %d jobs as notified', len(job_ids))
        except psycopg2.Error as e:
            logger.error('Error marking jobs as notified: %s', e)

    def cleanup_old_jobs(self, retention_days: int) -> int:
        if retention_days <= 0:
            return 0
        try:
            conn = self._get_connection()
            cursor = self._get_cursor(conn)
            cursor.execute(
                "DELETE FROM scraped_jobs WHERE created_at <= NOW() - INTERVAL '%s days'",
                (retention_days,),
            )
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            if deleted_count > 0:
                logger.info('Cleaned up %d old jobs (>%d days)', deleted_count, retention_days)
            return deleted_count
        except psycopg2.Error as e:
            logger.error('Error cleaning up old jobs: %s', e)
            return 0

    def get_stats(self) -> dict:
        """Return pipeline statistics including v2 fields."""
        try:
            conn = self._get_connection()
            cursor = self._get_cursor(conn)

            cursor.execute('SELECT COUNT(*) FROM scraped_jobs')
            total = cursor.fetchone()['count']

            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('SELECT COUNT(*) FROM scraped_jobs WHERE DATE(created_at) = %s', (today,))
            today_count = cursor.fetchone()['count']

            cursor.execute('SELECT source, COUNT(*) as count FROM scraped_jobs GROUP BY source ORDER BY count DESC')
            by_source = {row['source']: row['count'] for row in cursor.fetchall()}

            cursor.execute('SELECT COUNT(*) FROM scraped_jobs WHERE notified = 0')
            unnotified = cursor.fetchone()['count']

            cursor.execute('SELECT AVG(final_score) FROM scraped_jobs WHERE final_score > 0')
            avg_raw = cursor.fetchone()['avg']
            avg_score = round(float(avg_raw), 1) if avg_raw else 0.0

            cursor.execute(
                '''
                SELECT role_category, COUNT(*) as count
                FROM scraped_jobs
                WHERE role_category != '' AND DATE(created_at) = %s
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
                FROM scraped_jobs WHERE DATE(created_at) = %s
                ''',
                (today,),
            )
            row = cursor.fetchone()
            bands_today = {
                'EXCELLENT': int(row['excellent']) if row and row['excellent'] else 0,
                'STRONG': int(row['strong']) if row and row['strong'] else 0,
                'GOOD': int(row['good']) if row and row['good'] else 0,
                'BORDERLINE': int(row['borderline']) if row and row['borderline'] else 0,
                'SKIP': int(row['skip']) if row and row['skip'] else 0,
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
        except psycopg2.Error as e:
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
