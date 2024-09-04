import logging
from typing import Any, Protocol

from pydantic import JsonValue, TypeAdapter, ValidationError
from pydantic import Secret as PydanticSecret

from secretmanager.cache import CACHE
from secretmanager.settings import Settings

# TODO: can we make this dynamic as such user can provide their own TypeAdapter?
SecretValueAdapter = TypeAdapter[JsonValue](JsonValue)

logger = logging.getLogger(__name__)


class SecretValue(PydanticSecret[JsonValue]):
    """
    A wrapper class around pydantic Secret class.

    To retrieve the secret value, call `get_secret_value()` on the SecretValue instance.
    """

    def __init__(self, secret_value: JsonValue) -> None:
        """
        Constructor

        This class validates the input as JSON first and falls back to validating
        it as a Python object if the JSON validation fails.

        Args:
            secret_value: The secret value provided as a JSON string or a Python object.
        """
        try:
            value = SecretValueAdapter.validate_json(secret_value)  # type: ignore
        except ValidationError:
            value = SecretValueAdapter.validate_python(secret_value)
        super().__init__(value)


class AbstractSecretStore(Protocol):
    """
    A protocol that defines the interface for secret storage backends.

    This protocol should be implemented by any secret storage system

    Attributes:
        cacheable: Indicates whether the secrets in the store is cached.
    """

    cacheable: bool = False

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

    @staticmethod
    def _serialize(value: JsonValue) -> str:
        return SecretValueAdapter.dump_json(value).decode()

    def _construct_key(self, key: str) -> str:
        # considered duplicated keys for same class name!?
        return f"{self.__class__.__name__}:{key}"

    def _put_cache(self, key: str, value: JsonValue):
        if self.cacheable and Settings.cache.enabled:
            key = self._construct_key(key)
            value_json = self._serialize(value) if value is not None else None
            CACHE.put(key=key, value=value_json)

    def _get_cache(self, key: str) -> str | None:
        if self.cacheable and Settings.cache.enabled:
            key = self._construct_key(key)
            return CACHE.get(key=key)

    def _drop_cache(self, key: str) -> str | None:
        if self.cacheable and Settings.cache.enabled:
            key = self._construct_key(key)
            return CACHE.remove(key=key)
