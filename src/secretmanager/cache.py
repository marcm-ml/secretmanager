import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Generic, TypeVar

from secretmanager.settings import Settings

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
    def __init__(self, max_size: int, expires_in: int):
        self.lock = threading.Lock()
        self.cache: OrderedDict[str, CacheEntry[str | None]] = OrderedDict()
        self.max_cache_size = max_size
        self.refresh_period = expires_in

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256((key).encode()).hexdigest()

    def get(self, key: str):
        with self.lock:
            current_time = time.time()
            hashed_key = self._hash_key(key)

            if hashed_key in self.cache:
                entry = self.cache[hashed_key]
                if current_time - entry.timestamp <= self.refresh_period:
                    logger.debug("Cache hit for key %s", key)
                    self.cache.move_to_end(hashed_key)  # update last_accessed
                    return entry.value
                logger.debug("Cache expired for key %s", key)
                self.cache.pop(hashed_key)  # delete if expired

    def put(self, key: str, value: str | None):
        with self.lock:
            current_time = time.time()
            hashed_key = self._hash_key(key)

            logger.debug("Putting key %s into cache", key)
            # update entry and move to end
            self.cache[hashed_key] = CacheEntry(value, current_time)
            self.cache.move_to_end(hashed_key)

            # if length exceeded, pop least accessed item
            if len(self.cache) > self.max_cache_size:
                self.cache.popitem(last=False)

    def clear(self):
        """Clears the entire cache."""
        with self.lock:
            logger.debug("Clearing cache")
            self.cache.clear()

    def remove(self, key):
        """Remove a specific key from the cache."""
        with self.lock:
            hashed_key = self._hash_key(key)
            if hashed_key in self.cache:
                logger.debug("Deleting item %s from cache", key)
                del self.cache[hashed_key]


CACHE: LRUCache = LRUCache(max_size=Settings.cache.max_size, expires_in=Settings.cache.expires_in)
