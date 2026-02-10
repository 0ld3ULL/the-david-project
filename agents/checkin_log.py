"""
Anti-Repetition Checkin Log — prevents duplicate notifications.

SQLite-backed log that tracks every notification Oprah sends.
Before sending, callers check whether a duplicate (by topic or
message hash) was already sent within a configurable window.

Schema:
    id              INTEGER PRIMARY KEY
    topic           TEXT        — e.g. "schedule", "render", "distribute"
    message_hash    TEXT        — SHA-256 of the full message text
    message_summary TEXT        — first 200 chars for human readability
    action_type     TEXT        — e.g. "scheduled", "failed", "executed"
    details         TEXT        — extra context (optional)
    sent_at         TEXT        — ISO-8601 timestamp
"""

import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("data/checkin_log.db")


class CheckinLog:
    """
    Tracks sent notifications to prevent duplicates and spam.

    Usage:
        log = CheckinLog()
        if log.has_recently_sent_message(message):
            return  # skip duplicate
        send(message)
        log.log_notification("schedule", message, "scheduled")
    """

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Database setup
    # ------------------------------------------------------------------

    def _init_db(self):
        """Create table and index if they don't exist."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkin_log (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic           TEXT NOT NULL,
                    message_hash    TEXT NOT NULL,
                    message_summary TEXT NOT NULL DEFAULT '',
                    action_type     TEXT NOT NULL DEFAULT '',
                    details         TEXT NOT NULL DEFAULT '',
                    sent_at         TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkin_topic_sent
                ON checkin_log (topic, sent_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkin_hash_sent
                ON checkin_log (message_hash, sent_at)
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with WAL mode for concurrent reads."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_recently_notified(self, topic: str, hours: int = 4) -> bool:
        """
        Return True if *any* notification for this topic was sent
        within the last `hours` hours.
        """
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM checkin_log WHERE topic = ? AND sent_at > ? LIMIT 1",
                (topic, cutoff),
            ).fetchone()
        return row is not None

    def has_recently_sent_message(self, message: str, hours: int = 4) -> bool:
        """
        Return True if the exact same message (by SHA-256 hash) was
        already sent within the last `hours` hours.
        """
        msg_hash = self._hash(message)
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM checkin_log WHERE message_hash = ? AND sent_at > ? LIMIT 1",
                (msg_hash, cutoff),
            ).fetchone()
        return row is not None

    def log_notification(
        self,
        topic: str,
        message_summary: str,
        action_type: str = "",
        details: str = "",
    ):
        """Record a sent notification."""
        msg_hash = self._hash(message_summary)
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO checkin_log
                    (topic, message_hash, message_summary, action_type, details, sent_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (topic, msg_hash, message_summary[:200], action_type, details, now),
            )
            conn.commit()
        logger.debug(f"CheckinLog: recorded [{action_type}] for topic={topic}")

    def get_recent(self, hours: int = 24, limit: int = 20) -> list[dict]:
        """Return the most recent notifications within `hours`."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT topic, message_summary, action_type, details, sent_at
                FROM checkin_log
                WHERE sent_at > ?
                ORDER BY sent_at DESC
                LIMIT ?
                """,
                (cutoff, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def cleanup(self, days: int = 30):
        """Delete entries older than `days` days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM checkin_log WHERE sent_at < ?", (cutoff,)
            )
            conn.commit()
        deleted = result.rowcount
        if deleted:
            logger.info(f"CheckinLog: pruned {deleted} entries older than {days} days")
        return deleted

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash(message: str) -> str:
        """SHA-256 hex digest of a message string."""
        return hashlib.sha256(message.encode("utf-8")).hexdigest()
