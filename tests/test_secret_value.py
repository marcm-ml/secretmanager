from types import NoneType

import pytest

from secretmanager.store import SecretValue


@pytest.mark.parametrize(
    ("raw", "expected_type"),
    [
        ("null", NoneType),
        ("false", bool),
        ("true", bool),
        ("0", int),
        ("1.1", float),
        ("test", str),
        (r'["test", 123]', list),
        (r'{"test": 123}', dict),
        (r"[123]", list),
        (r'"[123]"', str),
    ],
)
def test_parse_value(raw, expected_type):
    value = SecretValue(raw)
    assert isinstance(value.get_secret_value(), expected_type)
