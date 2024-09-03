import logging
from pathlib import Path

from pydantic import JsonValue

from ..error import SecretAlreadyExists, SecretNotFoundError
from ..settings import Settings
from ..store import AbstractSecretStore, SecretValue

logger = logging.getLogger(__name__)


class DotEnvStore(AbstractSecretStore):
    def __init__(self, file: str | Path | None = None) -> None:
        try:
            import dotenv
        except ImportError as e:
            raise ImportError("Make sure to install with [dotenv]") from e

        _file = Path(file or Settings.dotenv.file or dotenv.find_dotenv() or ".env").resolve()
        if not _file.exists():
            raise ValueError(f"{_file} does not exist")
        if not _file.is_file():
            raise ValueError(f"{_file} is a directory")

        self._client = dotenv
        self._dotenv = dotenv.main.DotEnv(_file, verbose=False, interpolate=False, override=False)
        self._cache = self._dotenv.dict()
        self._file = _file

    def get(self, key: str):
        logger.info("Getting %s from dotenv store at %s", key, self._file)
        value = self._dotenv.get(key)

        if value is None:
            raise SecretNotFoundError(f"Secret {key} was not found in {self._file}")
        return SecretValue(value)

    def add(self, key: str, value: JsonValue):
        if key in self._dotenv.dict():
            raise SecretAlreadyExists(f"Secret {key} already exists")

        logger.info("Adding %s to dotenv store at %s", key, self._file)
        self._client.set_key(self._file, key, self._serialize(value))

        return SecretValue(self._serialize(value))

    def update(self, key: str, value: JsonValue):
        logger.info("Updating %s from dotenv store at %s", key, self._file)
        self._client.set_key(self._file, key, self._serialize(value))

        return SecretValue(self._serialize(value))

    def list_secret_keys(self):
        logger.info("List all secrets keys in dotenv store")
        return set(self._client.dotenv_values(self._file).keys())

    def list_secrets(self):
        logger.info("List all secrets in dotenv store")
        return {k: SecretValue(v) for k, v in self._client.dotenv_values(self._file).items()}

    def delete(self, key: str) -> None:
        logger.info("Deleting %s from dotenv store at %s", key, self._file)
        self._client.unset_key(self._file, key)
