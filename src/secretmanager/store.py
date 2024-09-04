import logging
from typing import Any, Protocol, TypeVar

from pydantic import JsonValue, TypeAdapter, ValidationError
from pydantic import Secret as PydanticSecret

from .cache import CACHE
from .settings import AWSSettings, DotEnvSettings, Settings, StoreSettings

logger = logging.getLogger(__name__)

SecretValue = PydanticSecret[JsonValue]


S = TypeVar("S", StoreSettings, AWSSettings, DotEnvSettings)


class AbstractSecretStore(Protocol[S]):
    """
    A protocol that defines the interface for secret storage backends.

    This protocol should be implemented by any secret storage system

    Attributes:
        cacheable: Indicates whether the secrets in the store is cached.
    """

    cacheable: bool = False
    store_settings: S = StoreSettings()
    # TODO: can we make this dynamic as such user can provide their own TypeAdapter?
    parser = TypeAdapter[JsonValue](JsonValue)

    def get(self, key: str) -> SecretValue:
        """
        Retrieves the secret associated with the given key.

        Args:
            key: The key for the secret to retrieve.
        """
        ...

    def add(self, key: Any, value: JsonValue) -> SecretValue:
        """
        Adds a new secret to the store.

        If the secret exists, an error is raised.

        Args:
            key: The key for the secret to be added.
            value: The value of the secret.
        """
        ...

    def update(self, key: Any, value: JsonValue) -> SecretValue:
        """
        Updates an existing or adds a new secret in the store.

        Args:
            key: The key for the secret to be updated.
            value: The new value of the secret.
        """
        ...

    def list_secret_keys(self) -> set[str]:
        """
        Lists all secrets keys in the store.
        """
        ...

    def list_secrets(self) -> dict[str, SecretValue]:
        """
        Lists all secrets in the store including their value.
        """
        ...

    def delete(self, key: str) -> None:
        """
        Deletes the secret associated with the given key.

        Args:
            key: The key for the secret to delete.
        """
        ...

    def __hash__(self) -> int:
        return hash(self.__class__.__name__)

    def _serialize(self, value: JsonValue) -> str:
        return self.parser.dump_json(value).decode()

    def _deserialize(self, raw_value: str) -> JsonValue:
        # value could be invalid-json, e.g. the store returns just a plain-text string
        try:
            value = self.parser.validate_json(raw_value)
        except ValidationError:
            value = self.parser.validate_python(raw_value)
        return value

    def _construct_key(self, key: str) -> str:
        # considered duplicated keys for same class name!?
        return f"{self.__class__.__name__}:{key}"

    def _put_cache(self, key: str, value: str | None):
        if self.cacheable and Settings.cache.enabled:
            key = self._construct_key(key)
            value_json = value if value is not None else None
            CACHE.put(key=key, value=value_json)

    def _get_cache(self, key: str) -> str | None:
        if self.cacheable and Settings.cache.enabled:
            key = self._construct_key(key)
            return CACHE.get(key=key)

    def _drop_cache(self, key: str) -> str | None:
        if self.cacheable and Settings.cache.enabled:
            key = self._construct_key(key)
            return CACHE.remove(key=key)
