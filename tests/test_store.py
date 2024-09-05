import pytest

from secretmanager.implementations.env import EnvVarStore


@pytest.mark.parametrize(
    ("expected", "raw"),
    [
        (None, "null"),
        (False, "false"),
        (True, "true"),
        (0, "0"),
        (1.1, "1.1"),
        ("test", r'"test"'),
        (["test", 123], r'["test",123]'),
        ({"test": 123}, r'{"test":123}'),
        ([123], r"[123]"),
        ("[123]", r'"[123]"'),
    ],
)
def test_deserialize_value(raw, expected):
    value = EnvVarStore()._deserialize(raw)
    assert isinstance(value, type(expected))
    assert value == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "null"),
        (False, "false"),
        (True, "true"),
        (0, "0"),
        (1.1, "1.1"),
        ("test", r'"test"'),
        (["test", 123], r'["test",123]'),
        ({"test": 123}, r'{"test":123}'),
        ([123], r"[123]"),
        ("[123]", r'"[123]"'),
    ],
)
def test_serialize_value(raw, expected):
    value = EnvVarStore()._serialize(raw)
    assert value == expected
