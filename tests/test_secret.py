import os

import pytest

from secretmanager.implementations.env import EnvVarStore
from secretmanager.secret import Secret
from secretmanager.settings import Settings, StoreSettings


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(os, "environ", {})
    monkeypatch.setenv("KEY", "VALUE")
    monkeypatch.setenv("SIMPLE", r'"VALUE"')
    monkeypatch.setenv("COMPLEX", r'{"MAPPING":{"KEY":"VALUE"},"LIST":[1,2,3],"STRING": "123","FLOAT": 1.2}')
    return EnvVarStore().__deepcopy__()


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("KEY", "VALUE"),
        ("SIMPLE", "VALUE"),
        ("COMPLEX", {"MAPPING": {"KEY": "VALUE"}, "LIST": [1, 2, 3], "STRING": "123", "FLOAT": 1.2}),
    ],
)
def test_secret(store, key, expected):
    secret = Secret(key, store=store)
    value = secret(store=store)

    assert value == expected
    assert type(value) is type(expected)


def test_equality(store):
    a = Secret("KEY", store=store)
    b = Secret("KEY", store=store)

    assert a == b
    _, _ = a(), b()
    assert a == b


def test_inequality(store):
    a = Secret("KEY", store=store)
    b = Secret("KEY", store=store)

    a()
    assert a != b


def test_mapping(store):
    a = Secret(
        "KEY", store=store, settings=StoreSettings(prefix="PREFIX_", suffix="_SUFFIX", mapping={"KEY": "MAPPED_KEY"})
    )

    mapped_key = a._get_mapped_key(store.settings)

    assert a._key == mapped_key
    assert mapped_key == "PREFIX_MAPPED_KEY_SUFFIX"
    assert a.key != mapped_key


def test_mapping_via_store(store):
    store.settings.prefix = "PREFIX_"
    store.settings.suffix = "_SUFFIX"
    store.settings.mapping = {"KEY": "MAPPED_KEY"}
    a = Secret("KEY", store=store)

    mapped_key = a._get_mapped_key(store.settings)

    assert a._key == mapped_key
    assert mapped_key == "PREFIX_MAPPED_KEY_SUFFIX"
    assert a.key != mapped_key


def test_mapping_via_settings(store):
    Settings.prefix = "PREFIX_"
    Settings.suffix = "_SUFFIX"
    Settings.mapping = {"KEY": "MAPPED_KEY"}
    a = Secret("KEY", store=store)

    mapped_key = a._get_mapped_key(store.settings)

    assert a._key == mapped_key
    assert mapped_key == "PREFIX_MAPPED_KEY_SUFFIX"
    assert a.key != mapped_key


def test_filter(store):
    a = Secret("KEY", store=store, settings=StoreSettings(filter_key=["KEY"]))

    assert a._filter_key(store.settings)
    assert a() is None


def test_filter_via_store(store):
    store.settings.filter_key = ["KEY"]
    a = Secret("KEY", store=store)

    assert a._filter_key(store.settings)
    assert a() is None


def test_filter_via_settings(store):
    Settings.filter_key = ["KEY"]
    a = Secret("KEY", store=store)

    assert a._filter_key(store.settings)
    assert a() is None
