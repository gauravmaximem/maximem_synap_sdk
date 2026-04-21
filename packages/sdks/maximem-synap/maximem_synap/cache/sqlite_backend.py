"""SQLite-based cache backend with WAL mode and TTL support."""

import sqlite3
import threading
import time
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from .backend import CacheBackend


logger = logging.getLogger("synap.sdk.cache")


class SQLiteCacheBackend(CacheBackend):
    """SQLite cache backend with WAL mode.

    Features:
    - WAL mode for concurrent read/write
    - TTL-based expiration
    - LRU eviction when size limit reached
    - Thread-safe with connection pooling
    """

    # Default limits
    MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB per file
    SWEEP_INTERVAL_SECONDS = 600  # 10 minutes

    def __init__(self, db_path: Path, max_size_bytes: int = None):
        self.db_path = db_path
        self.max_size_bytes = max_size_bytes or self.MAX_SIZE_BYTES

        # Thread-local connections
        self._local = threading.local()
        self._lock = threading.Lock()

        # Initialize database
        self._init_db()

        # Track last sweep time
        self._last_sweep = 0

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            self._local.conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
            )

            # Enable WAL mode for better concurrency
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-2000")  # 2MB cache

        return self._local.conn

    @contextmanager
    def _cursor(self):
        """Get a cursor with automatic commit/rollback."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    expires_at INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    last_access INTEGER NOT NULL,
                    size_bytes INTEGER NOT NULL
                )
            """)

            # Index for expiration sweeps
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_expires
                ON cache (expires_at)
            """)

            # Index for LRU eviction
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_lru
                ON cache (last_access)
            """)

            # Index for scope-based deletion (prefix matching)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_key_prefix
                ON cache (key)
            """)

    def _maybe_sweep(self) -> None:
        """Run expiration sweep if enough time has passed."""
        now = time.time()
        if now - self._last_sweep < self.SWEEP_INTERVAL_SECONDS:
            return

        with self._lock:
            if now - self._last_sweep < self.SWEEP_INTERVAL_SECONDS:
                return  # Double-check after acquiring lock

            self._last_sweep = now
            self._sweep_expired()

    def _sweep_expired(self) -> int:
        """Delete all expired entries. Returns count deleted."""
        now_ts = int(time.time())
        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM cache WHERE expires_at <= ?",
                (now_ts,)
            )
            deleted = cursor.rowcount
            if deleted > 0:
                logger.debug(f"Swept {deleted} expired cache entries")
            return deleted

    def _check_size_limit(self) -> None:
        """Evict LRU entries if over size limit."""
        with self._cursor() as cursor:
            cursor.execute("SELECT SUM(size_bytes) FROM cache")
            total_size = cursor.fetchone()[0] or 0

            if total_size <= self.max_size_bytes:
                return

            # Need to evict - delete oldest accessed entries
            target_size = int(self.max_size_bytes * 0.8)  # Free up to 80%
            to_free = total_size - target_size

            cursor.execute("""
                DELETE FROM cache WHERE key IN (
                    SELECT key FROM cache
                    ORDER BY last_access ASC
                    LIMIT (
                        SELECT COUNT(*) FROM cache WHERE size_bytes <= ?
                    )
                )
            """, (to_free,))

            logger.debug(f"LRU eviction freed {to_free} bytes")

    def get(self, key: str) -> Optional[bytes]:
        """Get value by key. Returns None if not found or expired."""
        self._maybe_sweep()

        now_ts = int(time.time())

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            value, expires_at = row

            # Check if expired (lazy expiration)
            if expires_at <= now_ts:
                cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None

            # Update last access time
            cursor.execute(
                "UPDATE cache SET last_access = ? WHERE key = ?",
                (now_ts, key)
            )

            return value

    def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        """Set value with TTL."""
        now_ts = int(time.time())
        expires_at = now_ts + ttl_seconds
        size_bytes = len(value)

        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO cache
                (key, value, expires_at, created_at, last_access, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key, value, expires_at, now_ts, now_ts, size_bytes))

        # Check size limit after insert
        self._check_size_limit()

    def delete(self, key: str) -> None:
        """Delete a specific key."""
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM cache WHERE key = ?", (key,))

    def clear_scope(self, scope_prefix: str) -> int:
        """Delete all keys matching scope prefix (for GDPR deletion)."""
        with self._cursor() as cursor:
            # Use LIKE with escaped prefix for prefix matching
            pattern = scope_prefix.replace("%", "\\%").replace("_", "\\_") + "%"
            cursor.execute(
                "DELETE FROM cache WHERE key LIKE ? ESCAPE '\\'",
                (pattern,)
            )
            return cursor.rowcount

    def clear_all(self) -> None:
        """Delete all cached data."""
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM cache")
        logger.info("Cache cleared")

    def stats(self) -> dict:
        """Get cache statistics."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as entry_count,
                    COALESCE(SUM(size_bytes), 0) as total_bytes,
                    COALESCE(MIN(created_at), 0) as oldest_entry,
                    COALESCE(MAX(created_at), 0) as newest_entry
                FROM cache
                WHERE expires_at > ?
            """, (int(time.time()),))

            row = cursor.fetchone()

            return {
                "backend": "sqlite",
                "enabled": True,
                "db_path": str(self.db_path),
                "entry_count": row[0],
                "total_bytes": row[1],
                "max_bytes": self.max_size_bytes,
                "utilization": row[1] / self.max_size_bytes if self.max_size_bytes > 0 else 0,
                "oldest_entry_ts": row[2],
                "newest_entry_ts": row[3],
            }

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
