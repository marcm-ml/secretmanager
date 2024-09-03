from typing import Any, Generic, TypeVar

from .cache import LRUCache
from .registry import get_store, get_store_settings
from .settings import Settings, StoreSettings
from .store import AbstractSecretStore, SecretValue

# TODO: option for sqllite cache?
CACHE: LRUCache["Secret"] = LRUCache(max_size=Settings.cache.max_size, expires_in=Settings.cache.expires_in)

V = TypeVar("V", str, SecretValue)


# TODO: individual secret settings?
class Secret(Generic[V]):
    def __init__(
        self, key: str, store: AbstractSecretStore[V] | None = None, settings: StoreSettings | None = None
    ) -> None:
        self.store = store
        self.key = key
        self._key = key  # potentially re-mapped key
        self.value: V = None  # type: ignore
        self.settings = settings or StoreSettings()
        self._last_used_store: AbstractSecretStore[V] = None  # type: ignore

    def __call__(self, store: AbstractSecretStore[V] | None = None) -> V | None:
        store = store or self.store or get_store(Settings.default_store, **Settings.default_store_kwargs)
        store_config = get_store_settings(Settings, store)
        self._last_used_store = store

        if self._filter_key(store_config):
            return None
        self._get_mapped_key(store_config)

        if Settings.cache.enabled and (cached_value := CACHE.get(self)):
            self.value = cached_value.value
            return cached_value.value

        self.value = store.get(self._key)

        if Settings.cache.enabled:
            CACHE.put(self)

        return self.value

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.key == other.key
            and self.value == other.value
            and self._last_used_store == other._last_used_store
        )

    def __hash__(self) -> int:
        return hash(self._key) + hash(self._last_used_store) + hash(self.settings)

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
