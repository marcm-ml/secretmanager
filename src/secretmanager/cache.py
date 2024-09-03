import atexit
import logging
import sqlite3
import threading
import time
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheEntry(Generic[T]):
    def __init__(self, value: T, timestamp: float):
        self.value = value
        self.timestamp = timestamp


class Singleton(type):
    """Ensures that only one database interface is created per unique key"""

    _instances = dict()

    def __call__(cls, *args, **kwargs):
        unique_key = (cls.__name__,)
        if unique_key not in cls._instances:
            cls._instances[unique_key] = super().__call__(*args, **kwargs)
        return cls._instances[unique_key]


class LRUCache(metaclass=Singleton):
    def __init__(self, db_path: str, max_size: int, expires_in: int):
        self.lock = threading.Lock()
        self.db_path = db_path
        self.max_cache_size = max_size
        self.refresh_period = expires_in
        self._initialized = False
        self._closed = True

        # Initialize SQLite DB
        if self._closed:
            self.conn = sqlite3.connect(self.db_path)
        self._closed = False
        if not self._initialized:
            atexit.register(self.close)
        self._initialize_db()

    def _initialize_db(self):
        """Create cache table if it doesn't exist."""
        if not self._initialized:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT,
                    value BLOB NULL,
                    timestamp REAL
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS timestamp_idx ON cache (timestamp)
            """)
            self.conn.commit()
            self._initialized = True

    def _get_cache_size(self) -> int:
        """Get the current number of items in the cache."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM cache")
        return cursor.fetchone()[0]

    def get(self, key: str) -> str | None:
        with self.lock:
            current_time = time.time()

            cursor = self.conn.execute("SELECT value, timestamp FROM cache WHERE key = ?", (key,))
            result = cursor.fetchone()

            if result:
                value, timestamp = result
                if current_time - timestamp <= self.refresh_period:
                    logger.debug("Cache hit for item %s", key)
                    # Update timestamp to refresh last accessed time
                    self.conn.execute("UPDATE cache SET timestamp = ? WHERE key = ?", (current_time, key))
                    self.conn.commit()
                    return value
                else:
                    logger.debug("Cache expired for item %s", key)
                    self.conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                    self.conn.commit()

    def put(self, key: str, value: str | None):
        with self.lock:
            current_time = time.time()

            logger.debug("Putting item %s into cache", key)
            self.conn.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, timestamp)
                VALUES (?, ?, ?)
                """,
                (key, value, current_time),
            )
            self.conn.commit()

            if self._get_cache_size() > self.max_cache_size:
                logger.debug("Cache full, removing oldest item")
                self.conn.execute(
                    """
                    DELETE FROM cache WHERE key IN (
                        SELECT key FROM cache ORDER BY timestamp ASC LIMIT 1
                    )
                    """
                )
                self.conn.commit()

    def clear(self):
        """Clears the entire cache."""
        with self.lock:
            logger.debug("Clearing cache")
            self.conn.execute("DELETE FROM cache")
            self.conn.commit()

    def remove(self, key: T):
        """Remove a specific key from the cache."""
        with self.lock:
            logger.debug("Deleting item %s from cache", key)
            self.conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self.conn.commit()

    def close(self):
        """Closes the database connection."""
        self.conn.close()
        self._closed = True
