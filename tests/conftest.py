import pytest
from pydantic_settings import SettingsConfigDict

from secretmanager.cache import LRUCache
from secretmanager.settings import SettingsFactory


# patch settings
@pytest.fixture(autouse=True)
def settings(monkeypatch) -> SettingsFactory:
    class TestSettingsFactory(SettingsFactory):
        model_config = SettingsFactory.model_config | SettingsConfigDict(env_prefix="SM_TEST_")

    settings = TestSettingsFactory()
    monkeypatch.setattr("secretmanager.settings.Settings", settings)
    return settings


# patch settings
@pytest.fixture(autouse=True)
def cache(monkeypatch, settings: SettingsFactory) -> LRUCache:
    cache = LRUCache(max_size=settings.cache.max_size, expires_in=settings.cache.expires_in)
    monkeypatch.setattr("secretmanager.cache.CACHE", cache)
    return cache
