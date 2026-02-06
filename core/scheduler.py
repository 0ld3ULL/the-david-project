"""
Content Scheduler - Schedule and manage timed content posts.

Uses APScheduler for job management with SQLite persistence.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)

# Default data directory
DATA_DIR = Path(os.environ.get("CLAWDBOT_DATA_DIR", "data"))


class ContentScheduler:
    """Manages scheduled content posts."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATA_DIR / "scheduler.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # APScheduler with SQLite persistence
        jobstores = {
            'default': SQLAlchemyJobStore(url=f'sqlite:///{self.db_path}')
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)

        # Callbacks for different content types
        self._executors: dict[str, Callable] = {}

        # Initialize metadata database
        self._init_db()

    def _init_db(self):
        """Initialize the metadata database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                content_type TEXT NOT NULL,
                content_data TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                executed_at TEXT,
                result TEXT
            )
        """)
        conn.commit()
        conn.close()

    def register_executor(self, content_type: str, executor: Callable):
        """Register an executor function for a content type."""
        self._executors[content_type] = executor
        logger.info(f"Registered executor for content type: {content_type}")

    async def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Content scheduler started")

    async def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Content scheduler stopped")

    def schedule(
        self,
        content_type: str,
        content_data: dict,
        scheduled_time: datetime,
        job_id: Optional[str] = None,
    ) -> str:
        """
        Schedule content for posting.

        Args:
            content_type: Type of content (e.g., "tweet", "video_tweet")
            content_data: Content payload
            scheduled_time: When to post
            job_id: Optional custom job ID

        Returns:
            Job ID
        """
        if not job_id:
            job_id = f"{content_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

        # Store metadata
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO scheduled_content
               (job_id, content_type, content_data, scheduled_time, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                job_id,
                content_type,
                json.dumps(content_data),
                scheduled_time.isoformat(),
                datetime.now().isoformat(),
            )
        )
        conn.commit()
        conn.close()

        # Schedule the job
        self.scheduler.add_job(
            self._execute_scheduled,
            trigger=DateTrigger(run_date=scheduled_time),
            args=[job_id],
            id=job_id,
            replace_existing=True,
        )

        logger.info(f"Scheduled {content_type} for {scheduled_time}: {job_id}")
        return job_id

    async def _execute_scheduled(self, job_id: str):
        """Execute a scheduled job."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT content_type, content_data FROM scheduled_content WHERE job_id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            logger.error(f"Scheduled job not found: {job_id}")
            return

        content_type, content_data_json = row
        content_data = json.loads(content_data_json)

        executor = self._executors.get(content_type)
        if not executor:
            logger.error(f"No executor for content type: {content_type}")
            self._update_status(job_id, "failed", "No executor registered")
            return

        try:
            logger.info(f"Executing scheduled job: {job_id}")
            result = await executor(content_data)
            self._update_status(job_id, "executed", json.dumps(result) if result else None)
            logger.info(f"Executed scheduled job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to execute scheduled job {job_id}: {e}")
            self._update_status(job_id, "failed", str(e))

    def _update_status(self, job_id: str, status: str, result: Optional[str] = None):
        """Update job status in database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """UPDATE scheduled_content
               SET status = ?, executed_at = ?, result = ?
               WHERE job_id = ?""",
            (status, datetime.now().isoformat(), result, job_id)
        )
        conn.commit()
        conn.close()

    def cancel(self, job_id: str) -> bool:
        """Cancel a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            self._update_status(job_id, "cancelled")
            logger.info(f"Cancelled scheduled job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def get_pending(self) -> list[dict]:
        """Get all pending scheduled content."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """SELECT * FROM scheduled_content
               WHERE status = 'pending'
               ORDER BY scheduled_time ASC"""
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_upcoming(self, hours: int = 24) -> list[dict]:
        """Get content scheduled for the next N hours."""
        cutoff = (datetime.now() + timedelta(hours=hours)).isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """SELECT * FROM scheduled_content
               WHERE status = 'pending' AND scheduled_time <= ?
               ORDER BY scheduled_time ASC""",
            (cutoff,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def reschedule(self, job_id: str, new_time: datetime) -> bool:
        """Reschedule an existing job."""
        try:
            self.scheduler.reschedule_job(
                job_id,
                trigger=DateTrigger(run_date=new_time)
            )
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "UPDATE scheduled_content SET scheduled_time = ? WHERE job_id = ?",
                (new_time.isoformat(), job_id)
            )
            conn.commit()
            conn.close()
            logger.info(f"Rescheduled {job_id} to {new_time}")
            return True
        except Exception as e:
            logger.error(f"Failed to reschedule {job_id}: {e}")
            return False


# Time slot suggestions for social media
def suggest_time_slots(count: int = 4) -> list[datetime]:
    """
    Suggest optimal posting times.

    Returns times spaced throughout the day at high-engagement periods.
    """
    now = datetime.now()
    slots = []

    # High engagement times (in local time)
    optimal_hours = [9, 12, 17, 20]  # 9am, noon, 5pm, 8pm

    for hour in optimal_hours:
        slot = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if slot <= now:
            slot += timedelta(days=1)
        slots.append(slot)

    # Sort and return requested count
    slots.sort()
    return slots[:count]
