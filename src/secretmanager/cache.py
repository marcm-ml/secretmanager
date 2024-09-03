import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheEntry(Generic[T]):
    def __init__(self, value: T, timestamp: float):
        self.value = value
        self.timestamp = timestamp


class LRUCache(Generic[T]):
    def __init__(self, max_size: int, expires_in: int):
        self.lock = threading.Lock()
        self.cache: OrderedDict[int, CacheEntry[T]] = OrderedDict()
        self.max_cache_size = max_size
        self.refresh_period = expires_in

    def _hash_key(self, item: Any):
        """Generate a unique hash for the object based on its attributes."""
        return int(hashlib.sha256(str(hash(item)).encode()).hexdigest(), 16)

    def get(self, item: T):
        with self.lock:
            hashed_key = self._hash_key(item)
            current_time = time.time()

            if hashed_key in self.cache:
                entry = self.cache[hashed_key]
                if current_time - entry.timestamp <= self.refresh_period:
                    logger.debug("Cache hit for item %s", item)
                    self.cache.move_to_end(hashed_key)  # update last_accessed
                    return entry.value
                logger.debug("Cache expired for item %s", item)
                self.cache.pop(hashed_key)  # delete if expired

    def put(self, item: T):
        with self.lock:
            hashed_key = self._hash_key(item)
            current_time = time.time()

            logger.debug("Putting item %s into cache", item)
            # update entry and move to end
            self.cache[hashed_key] = CacheEntry(item, current_time)
            self.cache.move_to_end(hashed_key)

            # if length exceeded, pop least accessed item
            if len(self.cache) > self.max_cache_size:
                self.cache.popitem(last=False)

    def clear(self):
        """Clears the entire cache."""
        with self.lock:
            logger.debug("Clearing cache")
            self.cache.clear()

    def remove(self, item):
        """Remove a specific key from the cache."""
        with self.lock:
            hashed_key = self._hash_key(item)
            if hashed_key in self.cache:
                logger.debug("Deleting item %s from cache", item)
                del self.cache[hashed_key]
