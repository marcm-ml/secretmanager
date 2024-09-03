import hashlib
import logging
from typing import Any

from .cache import LRUCache
from .registry import get_store, get_store_settings
from .settings import Settings, StoreSettings
from .store import AbstractSecretStore, SecretValue, SecretValueAdapter

CACHE: LRUCache = LRUCache(max_size=Settings.cache.max_size, expires_in=Settings.cache.expires_in)
logger = logging.getLogger(__name__)


# TODO: individual secret settings?
class Secret:
    def __init__(
        self, key: str, store: AbstractSecretStore | None = None, settings: StoreSettings | None = None
    ) -> None:
        self.store = store
        self.key = key
        self._key = key  # potentially re-mapped key
        self.value: SecretValue = None  # type: ignore
        self.settings = settings or StoreSettings()
        self._last_used_store: AbstractSecretStore = None  # type: ignore

    def __call__(self, store: AbstractSecretStore | None = None):
        store = store or self.store or get_store(Settings.default_store, **Settings.default_store_kwargs)
        store_config = get_store_settings(Settings, store)
        self._last_used_store = store

        if self._filter_key(store_config):
            return None

        self._get_mapped_key(store_config)

        if Settings.cache.enabled and (cached_value := self._get_cache()):
            self.value = SecretValue(cached_value)
            return self.value.get_secret_value()

        self.value = store.get(self._key)

        if Settings.cache.enabled:
            self._put_cache()

        return self.value.get_secret_value()

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.key == other.key
            and self.value == other.value
            and self._last_used_store == other._last_used_store
        )

    def _put_cache(self):
        hashed_key = self._hash_key()
        value_json = SecretValueAdapter.dump_json(self.value.get_secret_value()).decode() if self.value else None
        logger.debug("Putting secret '%s' into cache as item %s", self.key, hashed_key)
        return CACHE.put(key=hashed_key, value=value_json)

    def _get_cache(self):
        hashed_key = self._hash_key()
        logger.debug("Getting cache for secret '%s' for cache item %s", self.key, hashed_key)
        return CACHE.get(key=hashed_key)

    def _hash_key(self):
        return hashlib.sha256((self._key + self._last_used_store.__class__.__name__).encode()).hexdigest()

    def __hash__(self) -> int:
        return hash(self._key) + hash(self._last_used_store)

    def __str__(self) -> str:
        return f"Secret({self.key})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.key})"

    def _get_mapped_key(self, store_settings: StoreSettings) -> str:
        prefix = self.settings.prefix or store_settings.prefix or Settings.prefix
        suffix = self.settings.suffix or store_settings.suffix or Settings.suffix

        mapped_key = self.key
        if self.key in self.settings.mapping:
            mapped_key = self.settings.mapping[self.key]
        elif self.key in store_settings.mapping:
            mapped_key = store_settings.mapping[self.key]
        elif self.key in Settings.mapping:
            mapped_key = Settings.mapping[self.key]

        self._key = prefix + mapped_key + suffix
        return self._key

    def _filter_key(self, store_settings: StoreSettings):
        return (
            self.key in self.settings.filter_key
            or self.key in store_settings.filter_key
            or self.key in Settings.filter_key
        )
