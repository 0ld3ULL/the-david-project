"""
Goal Store - Tracks goals detected in conversations with Jono.

Goals are extracted from natural conversation by LLM classification.
Active goals provide context for David's responses.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data/goals.db")


@dataclass
class Goal:
    """A goal detected from conversation."""
    id: int
    title: str
    description: str
    status: str  # active, completed, archived
    priority: int  # 1-10
    source: str  # where it was detected
    tags: list[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str]


class GoalStore:
    """Tracks goals detected in conversations."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                priority INTEGER DEFAULT 5,
                source TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        """)

        # FTS5 for searching
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS goals_fts USING fts5(
                title, description, tags,
                content='goals',
                content_rowid='id'
            )
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS goals_ai AFTER INSERT ON goals BEGIN
                INSERT INTO goals_fts(rowid, title, description, tags)
                VALUES (new.id, new.title, new.description, new.tags);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS goals_ad AFTER DELETE ON goals BEGIN
                INSERT INTO goals_fts(goals_fts, rowid, title, description, tags)
                VALUES('delete', old.id, old.title, old.description, old.tags);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS goals_au AFTER UPDATE ON goals BEGIN
                INSERT INTO goals_fts(goals_fts, rowid, title, description, tags)
                VALUES('delete', old.id, old.title, old.description, old.tags);
                INSERT INTO goals_fts(rowid, title, description, tags)
                VALUES (new.id, new.title, new.description, new.tags);
            END
        """)

        conn.commit()
        conn.close()
        logger.info(f"Goals database initialized at {self.db_path}")

    def add(self, title: str, description: str = "", priority: int = 5,
            source: str = "", tags: list = None) -> int:
        """Add a new goal."""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        priority = max(1, min(10, priority))

        cursor.execute("""
            INSERT INTO goals (title, description, priority, source, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, description, priority, source, json.dumps(tags or []), now, now))

        goal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Goal added [{priority}/10]: {title}")
        return goal_id

    def complete(self, goal_id: int):
        """Mark a goal as completed."""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE goals SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE id = ?
        """, (now, now, goal_id))
        conn.commit()
        conn.close()

    def archive(self, goal_id: int):
        """Archive a goal."""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE goals SET status = 'archived', updated_at = ?
            WHERE id = ?
        """, (now, goal_id))
        conn.commit()
        conn.close()

    def get_active(self, limit: int = 20) -> list[Goal]:
        """Get all active goals, ordered by priority."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM goals WHERE status = 'active'
            ORDER BY priority DESC, created_at DESC
            LIMIT ?
        """, (limit,))
        goals = [self._to_goal(row) for row in cursor.fetchall()]
        conn.close()
        return goals

    def search(self, query: str, limit: int = 10) -> list[Goal]:
        """Search goals by text."""
        conn = self._get_conn()
        cursor = conn.cursor()
        safe_query = query.replace('"', '""')
        safe_query = f'"{safe_query}"'

        try:
            cursor.execute("""
                SELECT g.* FROM goals g
                JOIN goals_fts fts ON g.id = fts.rowid
                WHERE goals_fts MATCH ?
                ORDER BY g.priority DESC
                LIMIT ?
            """, (safe_query, limit))
            goals = [self._to_goal(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            cursor.execute("""
                SELECT * FROM goals
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY priority DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            goals = [self._to_goal(row) for row in cursor.fetchall()]

        conn.close()
        return goals

    def get_context(self) -> str:
        """Get formatted active goals for injection into responses."""
        goals = self.get_active(limit=10)
        if not goals:
            return ""

        lines = ["**Active Goals:**"]
        for g in goals:
            lines.append(f"- [{g.priority}/10] {g.title}")
            if g.description:
                lines.append(f"  {g.description[:100]}")
        return "\n".join(lines)

    def get_stats(self) -> dict:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM goals WHERE status = 'active'")
        active = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM goals WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM goals")
        total = cursor.fetchone()[0]
        conn.close()
        return {"active": active, "completed": completed, "total": total}

    def _to_goal(self, row) -> Goal:
        return Goal(
            id=row["id"], title=row["title"], description=row["description"],
            status=row["status"], priority=row["priority"], source=row["source"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"], updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )
