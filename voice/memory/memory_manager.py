"""
DEVA Memory Manager - Persistent memory for voice assistant.

Two memory systems:
1. DevaMemory - Individual user's context, preferences, conversation history
2. GroupMemory - Shared knowledge across all DEVA users (Unity/Unreal/Godot solutions)
"""

import json
import os
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, Tuple, List


class DevaMemory:
    """
    DEVA's memory system with:
    - User profile (name, preferences)
    - Conversation history (summarized)
    - Knowledge store (game dev solutions, learned info)
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "deva_memory.db"
            )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- User profile
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Conversation summaries
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary TEXT NOT NULL,
                    topics TEXT,  -- JSON array of topics
                    mood TEXT,    -- User's mood/sentiment
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Knowledge store
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,  -- gamedev, unity, unreal, godot, general
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,  -- Where learned (conversation, research)
                    confidence REAL DEFAULT 0.8,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                );

                -- Full-text search for knowledge
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    topic, content, category,
                    content='knowledge',
                    content_rowid='id'
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
                    INSERT INTO knowledge_fts(rowid, topic, content, category)
                    VALUES (new.id, new.topic, new.content, new.category);
                END;

                CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
                    INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, content, category)
                    VALUES('delete', old.id, old.topic, old.content, old.category);
                END;

                CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
                    INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, content, category)
                    VALUES('delete', old.id, old.topic, old.content, old.category);
                    INSERT INTO knowledge_fts(rowid, topic, content, category)
                    VALUES (new.id, new.topic, new.content, new.category);
                END;
            """)

    # === User Profile ===

    def set_user(self, key: str, value: str):
        """Set a user profile value (name, project, preferences)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profile (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))

    def get_user(self, key: str) -> Optional[str]:
        """Get a user profile value."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM user_profile WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else None

    def get_user_context(self) -> str:
        """Get full user context for prompts."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT key, value FROM user_profile").fetchall()

        if not rows:
            return ""

        lines = ["[User Profile]"]
        for key, value in rows:
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    # === Conversation Memory ===

    def save_conversation(self, summary: str, topics: list = None, mood: str = None):
        """Save a conversation summary."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conversations (summary, topics, mood)
                VALUES (?, ?, ?)
            """, (summary, json.dumps(topics or []), mood))

    def get_recent_conversations(self, limit: int = 5) -> list:
        """Get recent conversation summaries."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT summary, topics, mood, timestamp
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()

        return [
            {
                "summary": row[0],
                "topics": json.loads(row[1]) if row[1] else [],
                "mood": row[2],
                "timestamp": row[3]
            }
            for row in rows
        ]

    def get_conversation_context(self) -> str:
        """Get recent conversations for prompt context."""
        convos = self.get_recent_conversations(3)
        if not convos:
            return ""

        lines = ["[Recent Conversations]"]
        for c in convos:
            date = c["timestamp"][:10] if c["timestamp"] else "Unknown"
            lines.append(f"- {date}: {c['summary']}")
        return "\n".join(lines)

    # === Knowledge Store ===

    def learn(self, topic: str, content: str, category: str = "general", source: str = "conversation"):
        """Store new knowledge."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO knowledge (category, topic, content, source)
                VALUES (?, ?, ?, ?)
            """, (category, topic, content, source))

    def recall(self, query: str, limit: int = 3) -> list:
        """Search knowledge store."""
        with sqlite3.connect(self.db_path) as conn:
            # Escape special FTS characters
            safe_query = query.replace('"', '""')

            rows = conn.execute("""
                SELECT k.topic, k.content, k.category, k.confidence
                FROM knowledge k
                JOIN knowledge_fts fts ON k.id = fts.rowid
                WHERE knowledge_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (f'"{safe_query}"', limit)).fetchall()

            # Update last_used for recalled items
            if rows:
                conn.execute("""
                    UPDATE knowledge SET last_used = CURRENT_TIMESTAMP
                    WHERE topic IN (SELECT topic FROM knowledge_fts WHERE knowledge_fts MATCH ?)
                """, (f'"{safe_query}"',))

        return [
            {"topic": r[0], "content": r[1], "category": r[2], "confidence": r[3]}
            for r in rows
        ]

    def get_knowledge_context(self, query: str) -> str:
        """Get relevant knowledge for a query."""
        results = self.recall(query)
        if not results:
            return ""

        lines = ["[Relevant Knowledge]"]
        for r in results:
            lines.append(f"- {r['topic']}: {r['content']}")
        return "\n".join(lines)

    # === Combined Context ===

    def get_context(self, query: str = "") -> str:
        """Get full memory context for a prompt."""
        parts = []

        user_ctx = self.get_user_context()
        if user_ctx:
            parts.append(user_ctx)

        convo_ctx = self.get_conversation_context()
        if convo_ctx:
            parts.append(convo_ctx)

        if query:
            knowledge_ctx = self.get_knowledge_context(query)
            if knowledge_ctx:
                parts.append(knowledge_ctx)

        return "\n\n".join(parts)

    # === Stats ===

    def get_stats(self) -> dict:
        """Get memory statistics."""
        with sqlite3.connect(self.db_path) as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM user_profile").fetchone()[0]
            convo_count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            knowledge_count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]

        return {
            "user_profile_items": user_count,
            "conversations": convo_count,
            "knowledge_items": knowledge_count
        }

    def __repr__(self):
        stats = self.get_stats()
        return f"DevaMemory(user={stats['user_profile_items']}, convos={stats['conversations']}, knowledge={stats['knowledge_items']})"


class GroupMemory:
    """
    Shared knowledge base across all DEVA users.

    When DEVA solves a Unity/Unreal/Godot problem, the solution
    is stored here and available to all developers using DEVA.

    Categories:
    - unity: Unity Engine solutions
    - unreal: Unreal Engine solutions
    - godot: Godot Engine solutions
    - general: Cross-engine patterns
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "deva_group_knowledge.db"
            )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize group knowledge tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Shared solutions from all DEVA users
                CREATE TABLE IF NOT EXISTS solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    solution_hash TEXT UNIQUE,  -- Dedup based on content hash
                    engine TEXT NOT NULL,       -- unity, unreal, godot, general
                    category TEXT NOT NULL,     -- rendering, physics, networking, ui, audio, etc.
                    problem TEXT NOT NULL,      -- What was the issue
                    solution TEXT NOT NULL,     -- How it was solved
                    code_snippet TEXT,          -- Optional code example
                    tags TEXT,                  -- JSON array of keywords
                    upvotes INTEGER DEFAULT 0,  -- Community validation
                    verified BOOLEAN DEFAULT FALSE,
                    contributor_id TEXT,        -- Anonymous contributor hash
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                );

                -- Full-text search for solutions
                CREATE VIRTUAL TABLE IF NOT EXISTS solutions_fts USING fts5(
                    problem, solution, category, tags,
                    content='solutions',
                    content_rowid='id'
                );

                -- Triggers for FTS sync
                CREATE TRIGGER IF NOT EXISTS solutions_ai AFTER INSERT ON solutions BEGIN
                    INSERT INTO solutions_fts(rowid, problem, solution, category, tags)
                    VALUES (new.id, new.problem, new.solution, new.category, new.tags);
                END;

                CREATE TRIGGER IF NOT EXISTS solutions_ad AFTER DELETE ON solutions BEGIN
                    INSERT INTO solutions_fts(solutions_fts, rowid, problem, solution, category, tags)
                    VALUES('delete', old.id, old.problem, old.solution, old.category, old.tags);
                END;

                CREATE TRIGGER IF NOT EXISTS solutions_au AFTER UPDATE ON solutions BEGIN
                    INSERT INTO solutions_fts(solutions_fts, rowid, problem, solution, category, tags)
                    VALUES('delete', old.id, old.problem, old.solution, old.category, old.tags);
                    INSERT INTO solutions_fts(rowid, problem, solution, category, tags)
                    VALUES (new.id, new.problem, new.solution, new.category, new.tags);
                END;

                -- Track sync state for future cloud sync
                CREATE TABLE IF NOT EXISTS sync_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def _hash_solution(self, problem: str, solution: str) -> str:
        """Generate hash for deduplication."""
        content = f"{problem.lower().strip()}:{solution.lower().strip()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def contribute(
        self,
        engine: str,
        category: str,
        problem: str,
        solution: str,
        code_snippet: str = None,
        tags: List[str] = None,
        contributor_id: str = None
    ) -> bool:
        """
        Contribute a solution to the group knowledge base.

        Returns True if new solution added, False if duplicate.
        """
        solution_hash = self._hash_solution(problem, solution)

        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT INTO solutions
                    (solution_hash, engine, category, problem, solution, code_snippet, tags, contributor_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    solution_hash,
                    engine.lower(),
                    category.lower(),
                    problem,
                    solution,
                    code_snippet,
                    json.dumps(tags or []),
                    contributor_id
                ))
                return True
            except sqlite3.IntegrityError:
                # Duplicate - already exists
                return False

    def search(self, query: str, engine: str = None, limit: int = 5) -> List[dict]:
        """
        Search for solutions matching a query.

        Args:
            query: Search terms
            engine: Filter by engine (unity, unreal, godot) or None for all
            limit: Max results
        """
        with sqlite3.connect(self.db_path) as conn:
            safe_query = query.replace('"', '""')

            if engine:
                rows = conn.execute("""
                    SELECT s.problem, s.solution, s.code_snippet, s.engine,
                           s.category, s.tags, s.upvotes, s.verified
                    FROM solutions s
                    JOIN solutions_fts fts ON s.id = fts.rowid
                    WHERE solutions_fts MATCH ? AND s.engine = ?
                    ORDER BY s.upvotes DESC, rank
                    LIMIT ?
                """, (f'"{safe_query}"', engine.lower(), limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT s.problem, s.solution, s.code_snippet, s.engine,
                           s.category, s.tags, s.upvotes, s.verified
                    FROM solutions s
                    JOIN solutions_fts fts ON s.id = fts.rowid
                    WHERE solutions_fts MATCH ?
                    ORDER BY s.upvotes DESC, rank
                    LIMIT ?
                """, (f'"{safe_query}"', limit)).fetchall()

            # Update last_used for retrieved solutions
            if rows:
                conn.execute("""
                    UPDATE solutions SET last_used = CURRENT_TIMESTAMP
                    WHERE id IN (
                        SELECT rowid FROM solutions_fts WHERE solutions_fts MATCH ?
                    )
                """, (f'"{safe_query}"',))

        return [
            {
                "problem": r[0],
                "solution": r[1],
                "code_snippet": r[2],
                "engine": r[3],
                "category": r[4],
                "tags": json.loads(r[5]) if r[5] else [],
                "upvotes": r[6],
                "verified": bool(r[7])
            }
            for r in rows
        ]

    def get_context(self, query: str, engine: str = None) -> str:
        """Get relevant group knowledge for a query."""
        results = self.search(query, engine=engine, limit=3)
        if not results:
            return ""

        lines = ["[Community Solutions]"]
        for r in results:
            verified = " ✓" if r["verified"] else ""
            lines.append(f"- [{r['engine'].upper()}] {r['problem']}{verified}")
            lines.append(f"  Solution: {r['solution']}")
            if r["code_snippet"]:
                lines.append(f"  Code: {r['code_snippet'][:200]}...")
        return "\n".join(lines)

    def upvote(self, problem: str, solution: str) -> bool:
        """Upvote a solution (when it works for another user)."""
        solution_hash = self._hash_solution(problem, solution)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE solutions SET upvotes = upvotes + 1
                WHERE solution_hash = ?
            """, (solution_hash,))
            return cursor.rowcount > 0

    def get_stats(self) -> dict:
        """Get group knowledge statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM solutions").fetchone()[0]
            by_engine = conn.execute("""
                SELECT engine, COUNT(*) FROM solutions GROUP BY engine
            """).fetchall()
            verified = conn.execute(
                "SELECT COUNT(*) FROM solutions WHERE verified = 1"
            ).fetchone()[0]

        return {
            "total_solutions": total,
            "verified": verified,
            "by_engine": {r[0]: r[1] for r in by_engine}
        }

    def export_solutions(self, filepath: str = None) -> str:
        """Export all solutions to JSON for sharing with other devs."""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(self.db_path), "group_knowledge_export.json"
            )

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT solution_hash, engine, category, problem, solution,
                       code_snippet, tags, upvotes, verified, contributor_id, created_at
                FROM solutions
            """).fetchall()

        solutions = [{
            "hash": r[0], "engine": r[1], "category": r[2],
            "problem": r[3], "solution": r[4], "code_snippet": r[5],
            "tags": json.loads(r[6]) if r[6] else [], "upvotes": r[7],
            "verified": bool(r[8]), "contributor": r[9], "created": r[10]
        } for r in rows]

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"exported": datetime.now().isoformat(), "solutions": solutions}, f, indent=2)

        return filepath

    def import_solutions(self, filepath: str) -> dict:
        """Import solutions from another dev's export. Deduplicates automatically."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        added = 0
        skipped = 0

        for s in data.get("solutions", []):
            if self.contribute(
                engine=s["engine"],
                category=s["category"],
                problem=s["problem"],
                solution=s["solution"],
                code_snippet=s.get("code_snippet"),
                tags=s.get("tags"),
                contributor_id=s.get("contributor")
            ):
                added += 1
            else:
                skipped += 1

        return {"added": added, "skipped": skipped, "total": len(data.get("solutions", []))}

    def __repr__(self):
        stats = self.get_stats()
        engines = ", ".join(f"{k}:{v}" for k, v in stats.get("by_engine", {}).items())
        return f"GroupMemory(total={stats['total_solutions']}, verified={stats['verified']}, {engines})"


class GameMemory:
    """
    Project-specific memory for individual games.

    Stores everything DEVA learns about a specific game project:
    - Project metadata (name, engine, path, description)
    - Architecture (systems, patterns, key classes)
    - File mappings (important files and what they do)
    - Solved bugs (problems fixed in this project)
    - Team decisions and conventions
    - Dependencies and packages used
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "deva_games.db"
            )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize game memory tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Registered games
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    engine TEXT NOT NULL,           -- unity, unreal, godot
                    project_path TEXT,              -- Local path to project
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP
                );

                -- Architecture and systems knowledge per game
                CREATE TABLE IF NOT EXISTS game_architecture (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    system_name TEXT NOT NULL,      -- "Player Controller", "Inventory", "Networking"
                    description TEXT NOT NULL,
                    key_files TEXT,                 -- JSON array of file paths
                    patterns TEXT,                  -- Design patterns used
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                );

                -- Important files in each game
                CREATE TABLE IF NOT EXISTS game_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    purpose TEXT NOT NULL,          -- What this file does
                    key_classes TEXT,               -- JSON array of class names
                    dependencies TEXT,              -- JSON array of dependencies
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                );

                -- Bugs solved in each game
                CREATE TABLE IF NOT EXISTS game_bugs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    bug_description TEXT NOT NULL,
                    solution TEXT NOT NULL,
                    affected_files TEXT,            -- JSON array of files
                    root_cause TEXT,
                    prevention TEXT,                -- How to prevent in future
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                );

                -- Team decisions and conventions
                CREATE TABLE IF NOT EXISTS game_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    category TEXT NOT NULL,         -- "convention", "architecture", "dependency", "workflow"
                    decision TEXT NOT NULL,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                );

                -- General notes/knowledge per game
                CREATE TABLE IF NOT EXISTS game_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                );

                -- Full-text search across all game knowledge
                CREATE VIRTUAL TABLE IF NOT EXISTS game_knowledge_fts USING fts5(
                    game_name, content, category,
                    content='game_notes',
                    content_rowid='id'
                );
            """)

    # === Game Management ===

    def register_game(self, name: str, engine: str, project_path: str = None, description: str = None) -> int:
        """Register a new game project."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO games (name, engine, project_path, description)
                    VALUES (?, ?, ?, ?)
                """, (name, engine.lower(), project_path, description))
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Game already exists, return its ID
                row = conn.execute("SELECT id FROM games WHERE name = ?", (name,)).fetchone()
                return row[0] if row else None

    def get_game(self, name: str) -> Optional[dict]:
        """Get game by name."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT id, name, engine, project_path, description, last_accessed
                FROM games WHERE LOWER(name) = LOWER(?)
            """, (name,)).fetchone()

            if row:
                # Update last accessed
                conn.execute("UPDATE games SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?", (row[0],))
                return {
                    "id": row[0],
                    "name": row[1],
                    "engine": row[2],
                    "project_path": row[3],
                    "description": row[4],
                    "last_accessed": row[5]
                }
            return None

    def list_games(self, engine: str = None) -> List[dict]:
        """List all registered games, optionally filtered by engine."""
        with sqlite3.connect(self.db_path) as conn:
            if engine:
                rows = conn.execute("""
                    SELECT id, name, engine, description FROM games
                    WHERE engine = ? ORDER BY last_accessed DESC
                """, (engine.lower(),)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT id, name, engine, description FROM games
                    ORDER BY last_accessed DESC
                """).fetchall()

        return [{"id": r[0], "name": r[1], "engine": r[2], "description": r[3]} for r in rows]

    # === Architecture Knowledge ===

    def add_system(self, game_name: str, system_name: str, description: str,
                   key_files: List[str] = None, patterns: str = None, notes: str = None):
        """Document a system/component in the game."""
        game = self.get_game(game_name)
        if not game:
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO game_architecture (game_id, system_name, description, key_files, patterns, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (game["id"], system_name, description, json.dumps(key_files or []), patterns, notes))
        return True

    def get_systems(self, game_name: str) -> List[dict]:
        """Get all documented systems for a game."""
        game = self.get_game(game_name)
        if not game:
            return []

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT system_name, description, key_files, patterns, notes
                FROM game_architecture WHERE game_id = ?
            """, (game["id"],)).fetchall()

        return [{
            "system": r[0],
            "description": r[1],
            "key_files": json.loads(r[2]) if r[2] else [],
            "patterns": r[3],
            "notes": r[4]
        } for r in rows]

    # === File Knowledge ===

    def add_file(self, game_name: str, file_path: str, purpose: str,
                 key_classes: List[str] = None, dependencies: List[str] = None, notes: str = None):
        """Document an important file in the game."""
        game = self.get_game(game_name)
        if not game:
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO game_files (game_id, file_path, purpose, key_classes, dependencies, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (game["id"], file_path, purpose, json.dumps(key_classes or []), json.dumps(dependencies or []), notes))
        return True

    def get_files(self, game_name: str) -> List[dict]:
        """Get all documented files for a game."""
        game = self.get_game(game_name)
        if not game:
            return []

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT file_path, purpose, key_classes, dependencies, notes
                FROM game_files WHERE game_id = ?
            """, (game["id"],)).fetchall()

        return [{
            "path": r[0],
            "purpose": r[1],
            "key_classes": json.loads(r[2]) if r[2] else [],
            "dependencies": json.loads(r[3]) if r[3] else [],
            "notes": r[4]
        } for r in rows]

    # === Bug History ===

    def add_bug(self, game_name: str, bug_description: str, solution: str,
                affected_files: List[str] = None, root_cause: str = None, prevention: str = None):
        """Document a solved bug."""
        game = self.get_game(game_name)
        if not game:
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO game_bugs (game_id, bug_description, solution, affected_files, root_cause, prevention)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (game["id"], bug_description, solution, json.dumps(affected_files or []), root_cause, prevention))
        return True

    def get_bugs(self, game_name: str) -> List[dict]:
        """Get all solved bugs for a game."""
        game = self.get_game(game_name)
        if not game:
            return []

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT bug_description, solution, affected_files, root_cause, prevention, created_at
                FROM game_bugs WHERE game_id = ? ORDER BY created_at DESC
            """, (game["id"],)).fetchall()

        return [{
            "bug": r[0],
            "solution": r[1],
            "affected_files": json.loads(r[2]) if r[2] else [],
            "root_cause": r[3],
            "prevention": r[4],
            "date": r[5]
        } for r in rows]

    # === Decisions/Conventions ===

    def add_decision(self, game_name: str, category: str, decision: str, reasoning: str = None):
        """Document a team decision or convention."""
        game = self.get_game(game_name)
        if not game:
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO game_decisions (game_id, category, decision, reasoning)
                VALUES (?, ?, ?, ?)
            """, (game["id"], category, decision, reasoning))
        return True

    def get_decisions(self, game_name: str, category: str = None) -> List[dict]:
        """Get decisions for a game, optionally filtered by category."""
        game = self.get_game(game_name)
        if not game:
            return []

        with sqlite3.connect(self.db_path) as conn:
            if category:
                rows = conn.execute("""
                    SELECT category, decision, reasoning FROM game_decisions
                    WHERE game_id = ? AND category = ?
                """, (game["id"], category)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT category, decision, reasoning FROM game_decisions WHERE game_id = ?
                """, (game["id"],)).fetchall()

        return [{"category": r[0], "decision": r[1], "reasoning": r[2]} for r in rows]

    # === General Notes ===

    def add_note(self, game_name: str, topic: str, content: str):
        """Add a general note about the game."""
        game = self.get_game(game_name)
        if not game:
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO game_notes (game_id, topic, content)
                VALUES (?, ?, ?)
            """, (game["id"], topic, content))
        return True

    def get_notes(self, game_name: str) -> List[dict]:
        """Get all notes for a game."""
        game = self.get_game(game_name)
        if not game:
            return []

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT topic, content, created_at FROM game_notes WHERE game_id = ?
            """, (game["id"],)).fetchall()

        return [{"topic": r[0], "content": r[1], "date": r[2]} for r in rows]

    # === Context Generation ===

    def get_context(self, game_name: str) -> str:
        """Get full game context for prompts."""
        game = self.get_game(game_name)
        if not game:
            return ""

        lines = [f"[Game: {game['name']} ({game['engine'].upper()})]"]

        if game["description"]:
            lines.append(f"Description: {game['description']}")

        # Systems
        systems = self.get_systems(game_name)
        if systems:
            lines.append("\nSystems:")
            for s in systems[:5]:  # Limit to avoid too much context
                lines.append(f"- {s['system']}: {s['description'][:100]}")

        # Recent bugs (might be relevant)
        bugs = self.get_bugs(game_name)
        if bugs:
            lines.append("\nRecent solved bugs:")
            for b in bugs[:3]:
                lines.append(f"- {b['bug'][:80]}")

        # Key decisions
        decisions = self.get_decisions(game_name)
        if decisions:
            lines.append("\nConventions:")
            for d in decisions[:5]:
                lines.append(f"- [{d['category']}] {d['decision'][:80]}")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Get game memory statistics."""
        with sqlite3.connect(self.db_path) as conn:
            games = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
            systems = conn.execute("SELECT COUNT(*) FROM game_architecture").fetchone()[0]
            files = conn.execute("SELECT COUNT(*) FROM game_files").fetchone()[0]
            bugs = conn.execute("SELECT COUNT(*) FROM game_bugs").fetchone()[0]
            decisions = conn.execute("SELECT COUNT(*) FROM game_decisions").fetchone()[0]
            notes = conn.execute("SELECT COUNT(*) FROM game_notes").fetchone()[0]

        return {
            "games": games,
            "systems": systems,
            "files": files,
            "bugs": bugs,
            "decisions": decisions,
            "notes": notes
        }

    def export_game(self, game_name: str, filepath: str = None) -> str:
        """Export a game's knowledge to JSON for sharing."""
        game = self.get_game(game_name)
        if not game:
            return None

        if filepath is None:
            safe_name = game_name.lower().replace(" ", "_")
            filepath = os.path.join(
                os.path.dirname(self.db_path), f"game_{safe_name}_export.json"
            )

        export_data = {
            "exported": datetime.now().isoformat(),
            "game": game,
            "systems": self.get_systems(game_name),
            "files": self.get_files(game_name),
            "bugs": self.get_bugs(game_name),
            "decisions": self.get_decisions(game_name),
            "notes": self.get_notes(game_name)
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)

        return filepath

    def import_game(self, filepath: str) -> dict:
        """Import a game's knowledge from another dev's export."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        game_data = data.get("game", {})
        game_name = game_data.get("name")

        if not game_name:
            return {"error": "Invalid export file - no game name"}

        # Register/update game
        self.register_game(
            name=game_name,
            engine=game_data.get("engine", "unity"),
            project_path=game_data.get("project_path"),
            description=game_data.get("description")
        )

        counts = {"systems": 0, "files": 0, "bugs": 0, "decisions": 0, "notes": 0}

        # Import systems
        for s in data.get("systems", []):
            self.add_system(game_name, s["system"], s["description"],
                           s.get("key_files"), s.get("patterns"), s.get("notes"))
            counts["systems"] += 1

        # Import files
        for f in data.get("files", []):
            self.add_file(game_name, f["path"], f["purpose"],
                         f.get("key_classes"), f.get("dependencies"), f.get("notes"))
            counts["files"] += 1

        # Import bugs
        for b in data.get("bugs", []):
            self.add_bug(game_name, b["bug"], b["solution"],
                        b.get("affected_files"), b.get("root_cause"), b.get("prevention"))
            counts["bugs"] += 1

        # Import decisions
        for d in data.get("decisions", []):
            self.add_decision(game_name, d["category"], d["decision"], d.get("reasoning"))
            counts["decisions"] += 1

        # Import notes
        for n in data.get("notes", []):
            self.add_note(game_name, n["topic"], n["content"])
            counts["notes"] += 1

        return {"game": game_name, "imported": counts}

    def __repr__(self):
        stats = self.get_stats()
        return f"GameMemory(games={stats['games']}, systems={stats['systems']}, bugs={stats['bugs']})"
