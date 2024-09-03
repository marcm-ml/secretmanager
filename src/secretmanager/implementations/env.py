import logging
import os

from pydantic import JsonValue

from ..error import SecretAlreadyExists, SecretNotFoundError
from ..store import AbstractSecretStore, SecretValue

logger = logging.getLogger(__name__)


class EnvVarStore(AbstractSecretStore[SecretValue]):
    def get(self, key: str):
        if (value := os.environ.get(key)) is None:
            raise SecretNotFoundError(f"Secret {key} was not found in environment variables")
        logger.info("Getting key %s from environment variable store", key)
        return SecretValue(value)

    def add(self, key: str, value: JsonValue):
        logger.info("Adding key %s to environment variable store", key)
        if key in os.environ:
            raise SecretAlreadyExists(f"Secret {key} already exists in environment variables, use update instead")
        os.environ[key] = self._serialize(value)
        return SecretValue(self._serialize(value))

    def update(self, key: str, value: JsonValue):
        logger.info("Updating key %s in environment variable store", key)
        os.environ[key] = self._serialize(value)
        return SecretValue(self._serialize(value))

    def list_secret_keys(self):
        logger.info("List all secrets keys in environment variable store")
        return set(os.environ.keys())

    def list_secrets(self):
        logger.info("List all secrets in environment variable store")
        return {k: SecretValue(v) for k, v in os.environ.items()}

    def delete(self, key: str) -> None:
        if key in os.environ:
            logger.info("Deleting key %s from environment variable store", key)
            del os.environ[key]
