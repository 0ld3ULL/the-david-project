"""
Human-in-the-loop approval queue.

Every outbound action (tweet, Discord post, video publish, WhatsApp message)
enters this queue. The operator reviews via Telegram inline keyboards.
No exceptions. This is the safety backbone.

Storage: SQLite (simple, no external dependencies, survives restarts).
"""

import json
import sqlite3
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"      # Approved with modifications
    EXPIRED = "expired"    # Auto-expired after timeout


class ApprovalQueue:

    def __init__(self, db_path: str = "data/approval_queue.db",
                 expiry_hours: int = 24):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.expiry_hours = expiry_hours
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    action_data TEXT NOT NULL,
                    context_summary TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    operator_notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    executed_at TEXT,
                    cost_estimate REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_approvals_status
                ON approvals(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_approvals_project
                ON approvals(project_id)
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def submit(self, project_id: str, agent_id: str,
               action_type: str, action_data: dict,
               context_summary: str = "",
               cost_estimate: float = 0.0) -> int:
        """Submit an action for approval. Returns approval_id."""
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO approvals
                   (project_id, agent_id, action_type, action_data,
                    context_summary, cost_estimate, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, agent_id, action_type,
                 json.dumps(action_data), context_summary,
                 cost_estimate, datetime.now().isoformat())
            )
            return cursor.lastrowid

    def approve(self, approval_id: int, notes: str = "") -> dict:
        """Approve an action. Returns the approval record."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE approvals SET status='approved',
                   operator_notes=?, reviewed_at=? WHERE id=?""",
                (notes, datetime.now().isoformat(), approval_id)
            )
            row = conn.execute(
                "SELECT * FROM approvals WHERE id=?", (approval_id,)
            ).fetchone()
            return dict(row) if row else {}

    def reject(self, approval_id: int, reason: str = "") -> dict:
        """Reject an action."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE approvals SET status='rejected',
                   operator_notes=?, reviewed_at=? WHERE id=?""",
                (reason, datetime.now().isoformat(), approval_id)
            )
            return {"status": "rejected", "id": approval_id}

    def edit_and_approve(self, approval_id: int,
                         edited_data: dict, notes: str = "") -> dict:
        """Approve with modifications."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE approvals SET status='edited',
                   action_data=?, operator_notes=?, reviewed_at=?
                   WHERE id=?""",
                (json.dumps(edited_data), notes,
                 datetime.now().isoformat(), approval_id)
            )
            return {"status": "edited", "id": approval_id}

    def mark_executed(self, approval_id: int):
        """Mark an approved action as executed."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE approvals SET executed_at=? WHERE id=?""",
                (datetime.now().isoformat(), approval_id)
            )

    def get_pending(self, project_id: str | None = None) -> list[dict]:
        """Get all pending approvals."""
        with self._connect() as conn:
            if project_id:
                rows = conn.execute(
                    """SELECT * FROM approvals
                       WHERE status='pending' AND project_id=?
                       ORDER BY created_at""",
                    (project_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM approvals
                       WHERE status='pending'
                       ORDER BY created_at"""
                ).fetchall()
            return [dict(r) for r in rows]

    def get_by_id(self, approval_id: int) -> dict | None:
        """Get a single approval by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE id=?", (approval_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_approved_unexecuted(self) -> list[dict]:
        """Get actions that are approved/edited but not yet executed."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM approvals
                   WHERE status IN ('approved', 'edited')
                   AND executed_at IS NULL
                   ORDER BY reviewed_at"""
            ).fetchall()
            return [dict(r) for r in rows]

    def expire_old(self) -> int:
        """Expire pending approvals older than expiry_hours. Returns count."""
        cutoff = datetime.now().timestamp() - (self.expiry_hours * 3600)
        with self._connect() as conn:
            cursor = conn.execute(
                """UPDATE approvals SET status='expired'
                   WHERE status='pending'
                   AND created_at < ?""",
                (datetime.fromtimestamp(cutoff).isoformat(),)
            )
            return cursor.rowcount

    def get_stats(self, project_id: str | None = None) -> dict:
        """Get approval queue statistics."""
        with self._connect() as conn:
            where = "WHERE project_id=?" if project_id else ""
            params = (project_id,) if project_id else ()

            stats = {}
            for status in ApprovalStatus:
                row = conn.execute(
                    f"SELECT COUNT(*) as cnt FROM approvals {where}"
                    + (" AND " if where else " WHERE ")
                    + "status=?",
                    params + (status.value,)
                ).fetchone()
                stats[status.value] = row["cnt"]

            return stats

    def format_preview(self, approval: dict) -> str:
        """Format an approval record for human preview."""
        action_data = json.loads(approval["action_data"])
        action_type = approval["action_type"]

        if action_type == "tweet":
            return f'Tweet: "{action_data.get("text", "")}"'
        elif action_type == "thread":
            tweets = action_data.get("tweets", [])
            parts = [f"[{i+1}] {t}" for i, t in enumerate(tweets)]
            return "Thread:\n" + "\n---\n".join(parts)
        elif action_type in ("discord_message", "discord_announce"):
            channel = action_data.get("channel_name", "?")
            text = action_data.get("text", "")
            return f'Discord #{channel}: "{text}"'
        elif action_type == "whatsapp_send":
            target = action_data.get("target", "?")
            text = action_data.get("text", "")
            return f'WhatsApp to {target}: "{text}"'
        elif action_type == "reply":
            tweet_id = action_data.get("tweet_id", "?")
            text = action_data.get("text", "")
            return f'Reply to {tweet_id}:\n"{text}"'
        elif action_type == "video_create":
            script = action_data.get("script", "")
            return f'Video script: "{script[:200]}..."'
        else:
            return json.dumps(action_data, indent=2)[:500]
