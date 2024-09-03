import logging
from typing import Any

import botocore
import botocore.session
from pydantic import JsonValue

from ..store import AbstractSecretStore, SecretValue

logger = logging.getLogger(__name__)


class AWSSecretStore(AbstractSecretStore[SecretValue]):
    def __init__(
        self,
        kms_key: str | None = None,
        deletion_policy: str | int = "force",
        session_options: dict[str, Any] | None = None,
        client_options: dict[str, Any] | None = None,
    ) -> None:
        self._session_options = session_options or {}
        self._client_options = client_options or {}
        self._kms_key = kms_key

        # parse deletion policy
        self._deletion_policy: None | dict = None
        if deletion_policy == "force":
            self._deletion_policy = {"ForceDeleteWithoutRecovery": True}
        elif isinstance(deletion_policy, int):
            if 7 < deletion_policy > 30:
                raise ValueError("Deletion Policy can only be within 7 to 30 days")
            self._deletion_policy = {"RecoveryWindowInDays": deletion_policy}
        else:
            raise ValueError("Unknown value for deletion_policy parameter")

    def _get_client(self):
        session = botocore.session.get_session(**self._session_options)
        client = session.create_client("secretsmanager", **self._client_options)
        return client

    def get(self, key: str):
        client = self._get_client()
        logger.info("Getting key %s from aws secretmanager", key)
        response: dict[str, str] = client.get_secret_value(SecretId=key)
        return SecretValue(response["SecretString"])

    def add(self, key: str, value: JsonValue):
        client = self._get_client()
        kwargs = {}
        if self._kms_key:
            kwargs["KmsKeyId"] = self._kms_key
        logger.info("Adding key %s to aws secretmanager", key)
        client.create_secret(Name=key, SecretString=self._serialize(value), **kwargs)
        return SecretValue(self._serialize(value))

    def update(self, key: str, value: str):
        client = self._get_client()
        logger.info("Updating key %s in aws secretmanager", key)
        client.update_secret(SecretId=key, SecretString=self._serialize(value))
        return SecretValue(self._serialize(value))

    def list_secret_keys(self):
        client = self._get_client()
        response = client.list_secrets()
        logger.info("List all secrets keys in aws secretmanager")
        return {res["Name"] for res in response["SecretList"]}

    def list_secrets(self):
        secrets = self.list_secret_keys()
        return {key: self.get(key) for key in secrets}

    def delete(self, key: str) -> None:
        client = self._get_client()
        logger.info("Deleting key %s from aws secretmanager", key)
        client.delete_secret(SecretId=key, **self._deletion_policy)
