"""Local, owner-controlled long-term memory for Adam.

Memory is opt-in: only explicit owner commands save entries. This module does not
send memory to external providers. The database is stored with restrictive file
permissions where supported.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = "adam_memory.sqlite3"
MAX_MEMORY_CHARS = 8_000
MAX_QUERY_CHARS = 500
MAX_RESULTS = 100


class MemoryStore:
    """Small local memory store with explicit save, search, and listing operations."""

    def __init__(self, path: str | None = None) -> None:
        raw_path = path or os.getenv("ADAM_MEMORY_DB", DEFAULT_DB)
        self.path = Path(raw_path).expanduser()

    def _connect(self) -> sqlite3.Connection:
        parent = self.path.parent
        if not parent.exists() or not parent.is_dir():
            raise OSError("Memory database directory does not exist.")
        if self.path.is_symlink():
            raise OSError("Memory database must not be a symbolic link.")
        if self.path.exists() and not self.path.is_file():
            raise OSError("Memory database path is not a regular file.")

        connection = sqlite3.connect(self.path, timeout=5)
        try:
            if hasattr(os, "chmod"):
                os.chmod(self.path, 0o600)
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_created_at "
                "ON memories(created_at DESC)"
            )
            connection.commit()
            return connection
        except Exception:
            connection.close()
            raise

    @staticmethod
    def _validate_text(value: str, label: str, maximum: int) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{label} must be text.")
        value = value.strip()
        if not value or len(value) > maximum or "\x00" in value:
            raise ValueError(f"{label} must be between 1 and {maximum} characters.")
        return value

    def remember(self, content: str, category: str = "note") -> int:
        """Save a memory only when explicitly requested by the owner."""
        content = self._validate_text(content, "Memory", MAX_MEMORY_CHARS)
        category = self._validate_text(category, "Category", 40).lower()
        if not all(char.isalnum() or char in "_-" for char in category):
            raise ValueError("Category may contain only letters, numbers, '_' and '-'.")
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO memories(created_at, category, content) VALUES (?, ?, ?)",
                (timestamp, category, content),
            )
            return int(cursor.lastrowid)

    def list_recent(self, limit: int = 20) -> list[dict[str, object]]:
        """Return recent memories, bounded to avoid unbounded output."""
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise ValueError("Limit must be an integer.")
        limit = max(1, min(limit, MAX_RESULTS))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, created_at, category, content FROM memories "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"id": row[0], "created_at": row[1], "category": row[2], "content": row[3]}
            for row in rows
        ]

    def search(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        """Search stored memories using a simple case-insensitive substring match."""
        query = self._validate_text(query, "Search query", MAX_QUERY_CHARS)
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise ValueError("Limit must be an integer.")
        limit = max(1, min(limit, MAX_RESULTS))
        escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped_query}%"
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, created_at, category, content FROM memories "
                "WHERE content LIKE ? ESCAPE '\\' COLLATE NOCASE "
                "ORDER BY id DESC LIMIT ?",
                (pattern, limit),
            ).fetchall()
        return [
            {"id": row[0], "created_at": row[1], "category": row[2], "content": row[3]}
            for row in rows
        ]
