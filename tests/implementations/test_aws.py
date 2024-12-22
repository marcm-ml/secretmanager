from typing import Callable

import botocore.session
import pytest
from moto import mock_aws

from secretmanager.error import SecretAlreadyExistsError, SecretNotFoundError
from secretmanager.implementations.aws import AWSSecretStore


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def mocked_aws(aws_credentials):
    with mock_aws():
        yield


@pytest.fixture
def secretmanager(mocked_aws):
    session = botocore.session.get_session()
    client = session.create_client("secretsmanager")
    return client


@pytest.fixture
def create_secret(secretmanager):
    def wrapper(key, value):
        secretmanager.create_secret(Name=key, SecretString=value)

    return wrapper


@pytest.fixture
def store_factory(create_secret, populate: bool = False) -> Callable[..., AWSSecretStore]:
    create_secret("KEY", "VALUE")
    create_secret("SIMPLE", r'"VALUE"')
    create_secret("COMPLEX", r'{"MAPPING":{"KEY":"VALUE"},"LIST":[1,2,3],"STRING": "123","FLOAT": 1.2}')

    def wrapper(*args, **kwargs):
        return AWSSecretStore(*args, **kwargs)

    return wrapper


def test_getting_missing(store_factory):
    store = store_factory()
    with pytest.raises(SecretNotFoundError, match="was not found"):
        store.get(str(object().__hash__()))


def test_getting(store_factory):
    store = store_factory()
    val = store.get("KEY")

    assert val.get_secret_value() == "VALUE"


def test_adding(store_factory, secretmanager):
    store = store_factory()
    store.add("OTHER_KEY", "VALUE")

    assert secretmanager.get_secret_value(SecretId="OTHER_KEY")["SecretString"] == r'"VALUE"'


def test_adding_exists_error(store_factory):
    store = store_factory()

    with pytest.raises(SecretAlreadyExistsError, match="Secret KEY already exists"):
        store.add("KEY", "VALUE")


def test_list_secret_keys(store_factory):
    store = store_factory()
    store.add("TEST", "VALUE")
    secrets = store.list_secret_keys()

    assert "KEY" in secrets
    assert "TEST" in secrets


def test_list_secrets(store_factory):
    store = store_factory()
    store.add("TEST", {"key": "value"})
    secrets = store.list_secrets()

    assert "KEY" in secrets
    assert secrets["KEY"].get_secret_value() == "VALUE"
    assert "TEST" in secrets
    assert secrets["TEST"].get_secret_value() == {"key": "value"}


def test_delete(store_factory):
    store = store_factory()
    store.delete("KEY")
    secrets = store.list_secrets()
    assert "KEY" not in secrets
