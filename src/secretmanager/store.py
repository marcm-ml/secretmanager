import logging
from copy import copy
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, JsonValue, TypeAdapter, ValidationError
from pydantic import Secret as PydanticSecret

from secretmanager.cache import CACHE
from secretmanager.settings import AWSSettings, DotEnvSettings, Settings, StoreSettings

logger = logging.getLogger(__name__)

SecretValue = PydanticSecret[JsonValue]


S = TypeVar("S", StoreSettings, AWSSettings, DotEnvSettings)


class StoreCapabilities(BaseModel):
    """Model to indicate store's capabilities such as caching, read, writing"""

    cacheable: bool = False
    read: bool = False
    write: bool = False


class AbstractSecretStore(Protocol[S]):
    """
    A protocol that defines the interface for secret storage backends.

    This protocol should be implemented by any secret storage system

    Attributes:
        cacheable: Indicates whether the secrets in the store is cached.
    """

    capabilities: StoreCapabilities = StoreCapabilities(cacheable=False, read=False, write=False)
    settings: S = StoreSettings()
    # TODO: can we make this dynamic as such user can provide their own TypeAdapter?
    parser = TypeAdapter[JsonValue](JsonValue)

    def get(self, key: str) -> SecretValue: ...

    def add(self, key: Any, value: JsonValue) -> SecretValue: ...

    def update(self, key: Any, value: JsonValue) -> SecretValue: ...

    def list_secret_keys(self) -> set[str]: ...

    def list_secrets(self) -> dict[str, SecretValue]:
        """
        Lists all secrets in the store including their value.
        """
        return {k: self.get(k) for k in self.list_secret_keys()}

    def delete(self, key: str) -> None: ...

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.capabilities == self.capabilities
            and self.settings == other.settings
            and self.parser == other.parser
        )

    def __deepcopy__(self, memo: dict[int, Any] | None = None):
        cpy = copy(self)
        cpy.settings = self.settings.__deepcopy__()
        cpy.capabilities = self.capabilities.__deepcopy__()
        return cpy

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

    def _put_cache(self, key: str, value: str | None) -> None:
        if self.capabilities.cacheable and Settings.cache.enabled:
            key = self._construct_key(key)
            value_json = value if value is not None else None
            return CACHE.put(key=key, value=value_json)

    def _get_cache(self, key: str) -> str | None:
        if self.capabilities.cacheable and Settings.cache.enabled:
            key = self._construct_key(key)
            return CACHE.get(key=key)

    def _drop_cache(self, key: str) -> None:
        if self.capabilities.cacheable and Settings.cache.enabled:
            key = self._construct_key(key)
            return CACHE.remove(key=key)
