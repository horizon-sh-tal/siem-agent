"""SQLite-backed log buffer for Kafka outages."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List, Tuple


class LocalLogBuffer:
    """SQLite FIFO buffer for encrypted log payloads."""

    def __init__(self, db_path: str, max_size_mb: int = 100) -> None:
        self.db_path = db_path
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS log_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                topic TEXT,
                encrypted_data BLOB,
                size_bytes INTEGER
            )
            """
        )
        self.conn.commit()

    def add(self, topic: str, encrypted_data: bytes) -> None:
        """Add an encrypted log to the buffer."""
        timestamp = datetime.utcnow().isoformat()
        size_bytes = len(encrypted_data)

        current_size = self.get_total_size()
        while current_size + size_bytes > self.max_size_bytes:
            self.remove_oldest()
            current_size = self.get_total_size()

        self.conn.execute(
            "INSERT INTO log_buffer (timestamp, topic, encrypted_data, size_bytes) VALUES (?, ?, ?, ?)",
            (timestamp, topic, encrypted_data, size_bytes),
        )
        self.conn.commit()

    def get_total_size(self) -> int:
        """Get total buffer size in bytes."""
        cursor = self.conn.execute("SELECT SUM(size_bytes) FROM log_buffer")
        result = cursor.fetchone()[0]
        return int(result) if result else 0

    def remove_oldest(self) -> None:
        """Remove the oldest buffered entry."""
        self.conn.execute(
            "DELETE FROM log_buffer WHERE id = (SELECT MIN(id) FROM log_buffer)"
        )
        self.conn.commit()

    def get_all(self) -> List[Tuple[int, str, bytes]]:
        """Fetch all buffered entries in FIFO order."""
        cursor = self.conn.execute(
            "SELECT id, topic, encrypted_data FROM log_buffer ORDER BY id"
        )
        return list(cursor.fetchall())

    def remove(self, entry_id: int) -> None:
        """Remove a buffered entry by id."""
        self.conn.execute("DELETE FROM log_buffer WHERE id = ?", (entry_id,))
        self.conn.commit()

    def count(self) -> int:
        """Return number of buffered entries."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM log_buffer")
        return int(cursor.fetchone()[0])

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
