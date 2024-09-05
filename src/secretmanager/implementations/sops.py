import logging
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import JsonValue

from secretmanager.error import SecretNotFoundError
from secretmanager.settings import Settings, SopsSettings
from secretmanager.store import AbstractSecretStore, SecretValue, StoreCapabilities

logger = logging.getLogger(__name__)

SUPPORTED_FORMAT_TYPE = Literal["json"] | Literal["yaml"] | Literal["dotenv"] | Literal["binary"]


@lru_cache(maxsize=10)
def _get_sops_version(binary: str | Path):
    version_info = subprocess.run([binary, "-v"], capture_output=True).stdout.decode()
    installed_version = None
    if version := re.compile(r"\d\.\d\.\d+").search(version_info):
        installed_version = version.group()
    return installed_version


class SOPSSecretStore(AbstractSecretStore[SopsSettings]):
    def __init__(self, file: str | Path | None, sops_options: list[str] | None = None) -> None:
        self.settings = Settings.sops
        self.capabilities = StoreCapabilities(cacheable=True, read=True, write=False)

        # check file
        self._file = file or Settings.sops.file
        if self._file is None:
            raise ValueError("No sops-encrypted file has been provided")
        self._file = Path(self._file).expanduser().resolve()
        if not self._file.exists():
            raise ValueError("%s does not exists", self._file)
        if not self._file.is_file():
            raise ValueError("%s is not a file", self._file)

        self._binary = Settings.sops.binary or "sops"
        self._sops_version = _get_sops_version(self._binary)
        if self._sops_version and int(self._sops_version.split(".")[0]) != 3:
            raise ValueError(f"Sops version {self._sops_version} is not supported")

        # parse options and check
        self._options = sops_options or []
        self._options = [*self._options, *Settings.sops.options]
        self._options = [o for o in self._options if o in self._options]

        if "--in-place" in self._options or "-i" in self._options:
            raise ValueError("Inplace decryption is not supported")

        if "--output-type" in self._options or "-i" in self._options:
            raise ValueError("Argument --output-type is not supported")

        self._options += ["--output-type=json"]

    def _decrypt(self):
        proc = subprocess.run([self._binary, "-d", *self._options, str(self._file)], capture_output=True)
        try:
            proc.check_returncode()
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Failure in calling sops: {proc.stderr.decode()}")
        return proc.stdout

    def get(self, key: str):
        if cached_value := self._get_cache(key):
            return SecretValue(self._deserialize(cached_value))

        # put file content for caching
        raw_data = self._get_cache(str(self._file))
        if raw_data is None:
            logger.info("Getting %s from sops store at %s", key, self._file)
            raw_data = self._decrypt().decode()
            self._put_cache(str(self._file), raw_data)
        data = self._deserialize(raw_data)

        if isinstance(data, dict):
            value: JsonValue = data.get(key)
        else:
            value = data

        if value is None:
            raise SecretNotFoundError(f"Secret {key} was not found in {self._file}")

        return SecretValue(value)

    def add(self, key: str, value: JsonValue):
        raise NotImplementedError("This store only supports reading")

    def update(self, key: str, value: JsonValue):
        raise NotImplementedError("This store only supports reading")

    def list_secret_keys(self):
        logger.info("List all secrets keys in SOPS secret store")
        raw_data = self._get_cache(str(self._file)) or self._decrypt().decode()
        data = self._deserialize(raw_data)
        if isinstance(data, dict):
            return set(data.keys())

        raise NotImplementedError(
            "This method only works if the encrypted file can be loaded as a dict, "
            "e.g. it must contain key=value paris."
        )

    def list_secrets(self):
        return {k: self.get(k) for k in self.list_secret_keys()}

    def delete(self, key: str) -> None:
        raise NotImplementedError("This store only supports reading")
