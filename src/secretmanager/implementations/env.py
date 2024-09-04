import logging
import os

from pydantic import JsonValue

from secretmanager.error import SecretAlreadyExists, SecretNotFoundError
from secretmanager.settings import Settings, StoreSettings
from secretmanager.store import AbstractSecretStore, SecretValue

logger = logging.getLogger(__name__)


class EnvVarStore(AbstractSecretStore[StoreSettings]):
    cacheable = True
    store_settings = Settings.env

    def get(self, key: str):
        if cached_value := self._get_cache(key):
            return SecretValue(self._deserialize(cached_value))

        if (value := os.environ.get(key)) is None:
            raise SecretNotFoundError(f"Secret {key} was not found in environment variables")
        logger.info("Getting key %s from environment variable store", key)
        self._put_cache(key, value)
        return SecretValue(self._deserialize(value))

    def add(self, key: str, value: JsonValue):
        logger.info("Adding key %s to environment variable store", key)
        if key in os.environ:
            raise SecretAlreadyExists(f"Secret {key} already exists in environment variables, use update instead")
        os.environ[key] = self._serialize(value)
        self._put_cache(key, self._serialize(value))
        return SecretValue(value)

    def update(self, key: str, value: JsonValue):
        logger.info("Updating key %s in environment variable store", key)
        os.environ[key] = self._serialize(value)
        self._put_cache(key, self._serialize(value))
        return SecretValue(value)

    def list_secret_keys(self):
        logger.info("List all secrets keys in environment variable store")
        return set(os.environ.keys())

    def list_secrets(self):
        logger.info("List all secrets in environment variable store")
        return {k: SecretValue(v) for k, v in os.environ.items()}

    def delete(self, key: str) -> None:
        logger.info("Deleting key %s from environment variable store", key)
        del os.environ[key]
        self._drop_cache(key)
