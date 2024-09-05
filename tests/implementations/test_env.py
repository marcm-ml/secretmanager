import os

import pytest

from secretmanager.error import SecretAlreadyExists, SecretNotFoundError
from secretmanager.implementations.env import EnvVarStore


@pytest.fixture
def store_factory(monkeypatch) -> EnvVarStore:
    monkeypatch.setattr(os, "environ", {})
    monkeypatch.setenv("KEY", "VALUE")
    return EnvVarStore()


def test_getting_missing(store_factory):
    store = store_factory
    with pytest.raises(SecretNotFoundError, match="was not found in"):
        store.get(str(object().__hash__()))


def test_getting(store_factory):
    store = store_factory
    val = store.get("KEY")

    assert val.get_secret_value() == "VALUE"


def test_adding(store_factory):
    store = store_factory
    store.add("OTHER_KEY", "VALUE")

    assert "OTHER_KEY" in os.environ
    assert os.environ["OTHER_KEY"] == r'"VALUE"'


def test_adding_exists_error(store_factory):
    store = store_factory

    with pytest.raises(SecretAlreadyExists, match="Secret KEY already exists"):
        store.add("KEY", "VALUE")


def test_list_secret_keys(store_factory):
    store = store_factory
    store.add("TEST", "VALUE")
    secrets = store.list_secret_keys()

    assert "KEY" in secrets
    assert "TEST" in secrets


def test_list_secrets(store_factory):
    store = store_factory
    store.add("TEST", {"key": "value"})
    secrets = store.list_secrets()

    assert "KEY" in secrets
    assert secrets["KEY"].get_secret_value() == "VALUE"
    assert "TEST" in secrets
    assert secrets["TEST"].get_secret_value() == {"key": "value"}


def test_delete(store_factory):
    store = store_factory
    store.delete("KEY")
    secrets = store.list_secrets()
    secrets.pop("PYTEST_CURRENT_TEST")  # injected by default
    assert not secrets
