import logging
from typing import Any

from .registry import get_store
from .settings import Settings, StoreSettings
from .store import AbstractSecretStore, SecretValue

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
        self._last_used_store = store

        if self._filter_key(store.store_settings):
            return None

        self._get_mapped_key(store.store_settings)

        self.value = store.get(self._key)

        return self.value.get_secret_value()

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.key == other.key
            and self.value == other.value
            and self._last_used_store == other._last_used_store
        )

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
