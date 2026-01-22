"""
SQLite Store for EmberOS Memory.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional
from pathlib import Path
from datetime import datetime
import uuid

import aiosqlite

from emberos.core.constants import DB_PATH

logger = logging.getLogger(__name__)

# Schema definitions
SCHEMA = """
-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_message TEXT NOT NULL,
    agent_response TEXT,
    plan_json TEXT,
    results_json TEXT,
    context_json TEXT,
    duration_ms INTEGER,
    success BOOLEAN,
    embedding_id TEXT
);

-- Notes
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    tags TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    embedding_id TEXT,
    metadata TEXT
);

-- Tool Usage Statistics
CREATE TABLE IF NOT EXISTS tool_stats (
    tool_name TEXT PRIMARY KEY,
    call_count INTEGER DEFAULT 0,
    total_duration_ms INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_called DATETIME,
    avg_duration_ms INTEGER
);

-- User Preferences & Patterns
CREATE TABLE IF NOT EXISTS user_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT,
    pattern_json TEXT,
    confidence FLOAT,
    last_observed DATETIME,
    applied_count INTEGER DEFAULT 0
);

-- Configuration key-value store
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);
CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at);
CREATE INDEX IF NOT EXISTS idx_user_patterns_type ON user_patterns(pattern_type);
"""


class SQLiteStore:
    """
    SQLite-based persistent storage for EmberOS.

    Stores:
    - Conversation history
    - Notes
    - Tool usage statistics
    - User patterns and preferences
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._db: Optional[aiosqlite.Connection] = None

    async def start(self) -> None:
        """Initialize the database."""
        logger.info(f"Initializing SQLite store at {self.db_path}")

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect and create schema
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row

        await self._db.executescript(SCHEMA)
        await self._db.commit()

        logger.info("SQLite store initialized")

    async def stop(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    # ============ Conversations ============

    async def store_conversation(
        self,
        user_message: str,
        agent_response: str,
        plan: Optional[dict] = None,
        results: Optional[list] = None,
        context: Optional[dict] = None,
        duration_ms: int = 0,
        success: bool = True,
        embedding_id: Optional[str] = None
    ) -> str:
        """Store a conversation exchange."""
        conversation_id = str(uuid.uuid4())

        await self._db.execute(
            """
            INSERT INTO conversations 
            (id, user_message, agent_response, plan_json, results_json, context_json, duration_ms, success, embedding_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                user_message,
                agent_response,
                json.dumps(plan) if plan else None,
                json.dumps(results) if results else None,
                json.dumps(context) if context else None,
                duration_ms,
                success,
                embedding_id
            )
        )
        await self._db.commit()

        return conversation_id

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Get a conversation by ID."""
        async with self._db.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_conversation(row)
        return None

    async def get_recent_conversations(self, limit: int = 10) -> list[dict]:
        """Get recent conversations."""
        async with self._db.execute(
            "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_conversation(row) for row in rows]

    async def search_conversations(self, query: str, limit: int = 20) -> list[dict]:
        """Search conversations by text."""
        async with self._db.execute(
            """
            SELECT * FROM conversations 
            WHERE user_message LIKE ? OR agent_response LIKE ?
            ORDER BY timestamp DESC LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_conversation(row) for row in rows]

    def _row_to_conversation(self, row) -> dict:
        """Convert row to conversation dict."""
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "user_message": row["user_message"],
            "agent_response": row["agent_response"],
            "plan": json.loads(row["plan_json"]) if row["plan_json"] else None,
            "results": json.loads(row["results_json"]) if row["results_json"] else None,
            "context": json.loads(row["context_json"]) if row["context_json"] else None,
            "duration_ms": row["duration_ms"],
            "success": row["success"],
            "embedding_id": row["embedding_id"]
        }

    # ============ Notes ============

    async def create_note(
        self,
        title: str,
        content: str = "",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
        embedding_id: Optional[str] = None
    ) -> str:
        """Create a new note."""
        note_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        await self._db.execute(
            """
            INSERT INTO notes (id, title, content, tags, created_at, updated_at, embedding_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                title,
                content,
                json.dumps(tags) if tags else "[]",
                now,
                now,
                embedding_id,
                json.dumps(metadata) if metadata else None
            )
        )
        await self._db.commit()

        return note_id

    async def get_note(self, note_id: str) -> Optional[dict]:
        """Get a note by ID."""
        async with self._db.execute(
            "SELECT * FROM notes WHERE id = ?",
            (note_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_note(row)
        return None

    async def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
        embedding_id: Optional[str] = None
    ) -> bool:
        """Update a note."""
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        if embedding_id is not None:
            updates.append("embedding_id = ?")
            params.append(embedding_id)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(note_id)

        await self._db.execute(
            f"UPDATE notes SET {', '.join(updates)} WHERE id = ?",
            params
        )
        await self._db.commit()

        return True

    async def delete_note(self, note_id: str) -> bool:
        """Delete a note."""
        result = await self._db.execute(
            "DELETE FROM notes WHERE id = ?",
            (note_id,)
        )
        await self._db.commit()
        return result.rowcount > 0

    async def list_notes(
        self,
        limit: int = 50,
        tags: Optional[list[str]] = None,
        sort_by: str = "updated"
    ) -> list[dict]:
        """List notes with optional filtering."""
        order_col = {
            "created": "created_at",
            "updated": "updated_at",
            "title": "title"
        }.get(sort_by, "updated_at")

        query = f"SELECT * FROM notes ORDER BY {order_col} DESC LIMIT ?"
        params = [limit]

        if tags:
            # Filter by tags (JSON contains check)
            tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
            query = f"SELECT * FROM notes WHERE ({tag_conditions}) ORDER BY {order_col} DESC LIMIT ?"
            params = [f'%"{tag}"%' for tag in tags] + [limit]

        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_note(row) for row in rows]

    async def search_notes(self, query: str, limit: int = 20) -> list[dict]:
        """Search notes by text."""
        async with self._db.execute(
            """
            SELECT * FROM notes 
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY updated_at DESC LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_note(row) for row in rows]

    def _row_to_note(self, row) -> dict:
        """Convert row to note dict."""
        return {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "embedding_id": row["embedding_id"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else None
        }

    # ============ Tool Statistics ============

    async def record_tool_usage(
        self,
        tool_name: str,
        success: bool,
        duration_ms: int
    ) -> None:
        """Record tool usage statistics."""
        await self._db.execute(
            """
            INSERT INTO tool_stats (tool_name, call_count, total_duration_ms, success_count, error_count, last_called, avg_duration_ms)
            VALUES (?, 1, ?, ?, ?, ?, ?)
            ON CONFLICT(tool_name) DO UPDATE SET
                call_count = call_count + 1,
                total_duration_ms = total_duration_ms + excluded.total_duration_ms,
                success_count = success_count + excluded.success_count,
                error_count = error_count + excluded.error_count,
                last_called = excluded.last_called,
                avg_duration_ms = (total_duration_ms + excluded.total_duration_ms) / (call_count + 1)
            """,
            (
                tool_name,
                duration_ms,
                1 if success else 0,
                0 if success else 1,
                datetime.now().isoformat(),
                duration_ms
            )
        )
        await self._db.commit()

    async def get_tool_stats(self) -> list[dict]:
        """Get all tool statistics."""
        async with self._db.execute(
            "SELECT * FROM tool_stats ORDER BY call_count DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ============ User Patterns ============

    async def store_pattern(
        self,
        pattern_type: str,
        pattern: dict,
        confidence: float = 0.5
    ) -> int:
        """Store a user pattern."""
        result = await self._db.execute(
            """
            INSERT INTO user_patterns (pattern_type, pattern_json, confidence, last_observed)
            VALUES (?, ?, ?, ?)
            """,
            (pattern_type, json.dumps(pattern), confidence, datetime.now().isoformat())
        )
        await self._db.commit()
        return result.lastrowid

    async def get_patterns(self, pattern_type: Optional[str] = None) -> list[dict]:
        """Get user patterns."""
        if pattern_type:
            query = "SELECT * FROM user_patterns WHERE pattern_type = ? ORDER BY confidence DESC"
            params = (pattern_type,)
        else:
            query = "SELECT * FROM user_patterns ORDER BY confidence DESC"
            params = ()

        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "type": row["pattern_type"],
                    "pattern": json.loads(row["pattern_json"]),
                    "confidence": row["confidence"],
                    "last_observed": row["last_observed"],
                    "applied_count": row["applied_count"]
                }
                for row in rows
            ]

    # ============ Configuration ============

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        async with self._db.execute(
            "SELECT value FROM config WHERE key = ?",
            (key,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except json.JSONDecodeError:
                    return row["value"]
        return default

    async def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        json_value = json.dumps(value) if not isinstance(value, str) else value

        await self._db.execute(
            """
            INSERT INTO config (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, json_value, datetime.now().isoformat())
        )
        await self._db.commit()

