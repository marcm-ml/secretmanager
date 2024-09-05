from collections.abc import Callable
from pathlib import Path

import pytest

from secretmanager.error import SecretAlreadyExists, SecretNotFoundError
from secretmanager.implementations.dotenv import DotEnvStore


def _store_factory(tmp_path: Path, populate: bool = False) -> Callable[[bool], DotEnvStore]:
    """Get DotEnvStore instance with a existing file either pre-populated or not"""

    def wrapper(*args, **kwargs):
        file = tmp_path / ".env"
        file.touch()
        if populate:
            with file.open("w") as f:
                f.write("KEY=VALUE")
        return DotEnvStore(file=file, *args, **kwargs).__deepcopy__()

    return wrapper


@pytest.fixture
def empty_store_factory(tmp_path) -> Callable[..., DotEnvStore]:
    return _store_factory(tmp_path=tmp_path, populate=False)


@pytest.fixture
def populated_store_factory(tmp_path) -> Callable[..., DotEnvStore]:
    return _store_factory(tmp_path=tmp_path, populate=True)


def test_is_dir():
    with pytest.raises(ValueError, match="does not exist"):
        DotEnvStore(file="12312313123123123")


def test_missing_file(tmp_path):
    with pytest.raises(ValueError, match="is a directory"):
        DotEnvStore(file=tmp_path)


def test_getting_missing(empty_store_factory):
    store = empty_store_factory()
    with pytest.raises(SecretNotFoundError, match="was not found in"):
        store.get(str(object().__hash__()))


def test_getting(populated_store_factory):
    store = populated_store_factory()
    val = store.get("KEY")

    assert val.get_secret_value() == "VALUE"


def test_adding(empty_store_factory):
    store = empty_store_factory()
    store.add("KEY", "VALUE")

    store.cacheable = False
    val = store.get("KEY")
    assert val.get_secret_value() == "VALUE"


def test_adding_exists_error(populated_store_factory):
    store = populated_store_factory()

    with pytest.raises(SecretAlreadyExists, match="Secret KEY already exists"):
        store.add("KEY", "VALUE")


def test_list_secret_keys(populated_store_factory):
    store = populated_store_factory()
    store.add("TEST", {"key": "value"})
    secrets = store.list_secret_keys()

    assert "KEY" in secrets
    assert "TEST" in secrets


def test_list_secrets(populated_store_factory):
    store = populated_store_factory()
    store.add("TEST", {"key": "value"})
    secrets = store.list_secrets()

    assert "KEY" in secrets
    assert secrets["KEY"].get_secret_value() == "VALUE"
    assert "TEST" in secrets
    assert secrets["TEST"].get_secret_value() == {"key": "value"}


def test_delete(populated_store_factory):
    store = populated_store_factory()
    store.delete("KEY")
    assert not store.list_secrets()
