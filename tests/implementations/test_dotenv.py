from collections.abc import Callable
from pathlib import Path

import pytest

from secretmanager.error import SecretAlreadyExistsError, SecretNotFoundError
from secretmanager.implementations.dotenv import DotEnvStore


@pytest.fixture
def store_factory(tmp_path: Path) -> Callable[[bool], DotEnvStore]:
    """Get DotEnvStore instance with a existing file either pre-populated or not"""

    def wrapper(*args, **kwargs):
        file = tmp_path / ".env"
        file.touch()
        with file.open("w") as f:
            f.write("KEY=VALUE")
        return DotEnvStore(file=file, *args, **kwargs)

    return wrapper


def test_is_dir():
    with pytest.raises(ValueError, match="does not exist"):
        DotEnvStore(file="12312313123123123")


def test_missing_file(tmp_path):
    with pytest.raises(ValueError, match="is a directory"):
        DotEnvStore(file=tmp_path)


def test_getting_missing(store_factory):
    store = store_factory()
    with pytest.raises(SecretNotFoundError, match="was not found in"):
        store.get(str(object().__hash__()))


def test_getting(store_factory):
    store = store_factory()
    val = store.get("KEY")

    assert val.get_secret_value() == "VALUE"


def test_adding(store_factory):
    store = store_factory()
    store.add("OTHER_KEY", "VALUE")

    store.cacheable = False
    val = store.get("OTHER_KEY")
    assert val.get_secret_value() == "VALUE"


def test_adding_exists_error(store_factory):
    store = store_factory()

    with pytest.raises(SecretAlreadyExistsError, match="Secret KEY already exists"):
        store.add("KEY", "VALUE")


def test_list_secret_keys(store_factory):
    store = store_factory()
    store.add("TEST", {"key": "value"})
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
    assert not store.list_secrets()
