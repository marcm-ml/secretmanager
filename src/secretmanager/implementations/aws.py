import logging
from typing import Any, Literal

import botocore
import botocore.session
from botocore.exceptions import ClientError
from pydantic import JsonValue

from secretmanager.error import SecretAlreadyExistsError, SecretNotFoundError
from secretmanager.settings import AWSSettings, Settings
from secretmanager.store import AbstractSecretStore, SecretValue, StoreCapabilities

logger = logging.getLogger(__name__)


class AWSSecretStore(AbstractSecretStore[AWSSettings]):
    def __init__(
        self,
        kms_key: str | None = None,
        session_options: dict[str, Any] | None = None,
        client_options: dict[str, Any] | None = None,
    ) -> None:
        self.capabilities = StoreCapabilities(cacheable=True, read=True, write=True)
        self.settings = Settings.aws

        self._session_options = session_options or {}
        self._client_options = client_options or {}
        self._kms_key = kms_key
        self._deletion_policy = self._parse_deletion_policy(self.settings.deletion_policy)

    def _parse_deletion_policy(self, deletion_policy: Literal["force"] | int | None):
        if deletion_policy is None:
            return {}
        elif deletion_policy == "force":
            return {"ForceDeleteWithoutRecovery": True}
        elif isinstance(deletion_policy, int):
            if 7 < deletion_policy > 30:
                raise ValueError("Deletion Policy can only be within 7 to 30 days")
            return {"RecoveryWindowInDays": deletion_policy}
        else:
            raise ValueError("Unknown value for deletion_policy parameter")

    def _get_client(self):
        session = botocore.session.get_session(**self._session_options)
        client = session.create_client("secretsmanager", **self._client_options)
        return client

    def get(self, key: str):
        client = self._get_client()
        logger.info("Getting key %s from aws secretmanager", key)

        if cached_value := self._get_cache(key):
            return SecretValue(self._deserialize(cached_value))
        try:
            value: str = client.get_secret_value(SecretId=key)["SecretString"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise SecretNotFoundError(f"Secret {key} was not found in AWS SecretManager") from e
            else:
                raise e
        self._put_cache(key, value)
        return SecretValue(self._deserialize(value))

    def add(self, key: str, value: JsonValue):
        client = self._get_client()
        kwargs = {}
        if self._kms_key:
            kwargs["KmsKeyId"] = self._kms_key
        logger.info("Adding key %s to aws secretmanager", key)
        try:
            client.create_secret(Name=key, SecretString=self._serialize(value), **kwargs)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceExistsException":
                raise SecretAlreadyExistsError(f"Secret {key} already exists") from e
        self._put_cache(key, self._serialize(value))
        return SecretValue(value)

    def update(self, key: str, value: JsonValue):
        client = self._get_client()
        logger.info("Updating key %s in aws secretmanager", key)
        client.update_secret(SecretId=key, SecretString=self._serialize(value))
        self._put_cache(key, self._serialize(value))
        return SecretValue(value)

    def list_secret_keys(self):
        client = self._get_client()
        response = client.list_secrets()
        logger.info("List all secrets keys in aws secretmanager")
        return {res["Name"] for res in response["SecretList"]}

    def list_secrets(self):
        secrets = self.list_secret_keys()
        res: dict[str, SecretValue] = {}
        for key in secrets:
            try:
                res[key] = self.get(key)
            except ClientError as e:
                logger.debug("Failed to get secret due to: %s", e.response["Error"]["Message"])
        return res

    def delete(self, key: str) -> None:
        client = self._get_client()
        logger.info("Deleting key %s from aws secretmanager", key)
        kwargs = {} | self._deletion_policy
        client.delete_secret(SecretId=key, **kwargs)
        self._drop_cache(key)
