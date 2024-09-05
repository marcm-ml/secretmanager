import pytest

from secretmanager.cache import CACHE
from secretmanager.settings import Settings, SettingsFactory


# make global settings function scoped
@pytest.fixture(autouse=True)
def settings():
    Settings.model_config.update(env_prefix="SM_TEST_")
    Settings.__init__()
    yield Settings
    Settings.__init__()


# make global cache function scoped
@pytest.fixture(autouse=True)
def cache(settings: SettingsFactory):
    CACHE.max_cache_size = settings.cache.max_size
    CACHE.expires_in = settings.cache.expires_in
    yield CACHE
    CACHE.clear()
