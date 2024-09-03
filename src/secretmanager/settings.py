from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, JsonValue
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
    YamlConfigSettingsSource,
)

RELATIVE_CONFIG_BASE_PATH = Path(".secretmanager").resolve()
XDG_CONFIG_BASE_PATH = Path("~", ".config", "secretmanager").expanduser().resolve()


class StoreChoice(str, Enum):
    DOTENV = "DOTENV"
    ENV = "ENV"
    AWS = "AWS"
    AZURE = "AZURE"
    BITWARDEN = "BITWARDEN"
    GOOGLE = "GC"


class CacheSettings(BaseModel):
    enabled: bool = Field(default=True, description="Whether to enable caching")
    max_size: int = Field(
        default=2**12, description="Max cache size after which the least accessed elemets are dropped"
    )
    expires_in: int = Field(
        default=1 * 60 * 60, description="Time in seconds since last access after which the cache entry expires"
    )


class StoreSettings(BaseModel):
    prefix: str = Field(default="", description="Prefix to prepend to all secret keys, specific to this store")
    suffix: str = Field(default="", description="Suffix to append to all secret keys, specific to this store")
    mapping: dict[str, str] = Field(
        default_factory=dict, description="Key-Value mapping where secret keys would be mapped to another key"
    )
    filter_key: list[str] = Field(
        default_factory=list, description="List of keys to filter, is applied on an unmapped key"
    )


class DotEnvSettings(StoreSettings):
    file: str | Path | None = Field(default=None, description="Default .env filepath")


class SettingsFactory(BaseSettings):
    prefix: str = Field(default="", description="Prefix to prepend to all secret keys globally")
    suffix: str = Field(default="", description="Suffix to append to all secret keys globally")
    mapping: dict[str, str] = Field(
        default_factory=dict, description="Key-Value mapping where secret keys would be mapped to another key globally"
    )
    filter_key: list[str] = Field(
        default_factory=list, description="List of keys to filter globally, is applied on an unmapped key"
    )
    default_store: str = Field(default=StoreChoice.ENV.value, description="Default store to use")
    default_store_kwargs: dict[str, JsonValue] = Field(
        default_factory=dict, description="Kwargs passed to the default store"
    )
    cache: CacheSettings = Field(default_factory=CacheSettings, description="Cache settings")

    env: StoreSettings = Field(default_factory=StoreSettings, description="Environment variable store settings")
    dotenv: DotEnvSettings = Field(default_factory=DotEnvSettings, description="Dotenv store settings")
    aws: StoreSettings = Field(default_factory=StoreSettings, description="AWS store settings")

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="SM_",
        env_nested_delimiter="__",
        env_parse_enums=True,
        case_sensitive=False,
        validate_assignment=True,
        cache_strings="all",
        pyproject_toml_table_header=("tool", "secretmanager"),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            TomlConfigSettingsSource(
                settings_cls=settings_cls,
                toml_file=[
                    "secretmanager.toml",
                    RELATIVE_CONFIG_BASE_PATH / "config.toml",
                    XDG_CONFIG_BASE_PATH / "config.toml",
                ],
            ),
            YamlConfigSettingsSource(
                settings_cls=settings_cls,
                yaml_file=[
                    "secretmanager.yaml",
                    RELATIVE_CONFIG_BASE_PATH / "config.yaml",
                    XDG_CONFIG_BASE_PATH / "config.yaml",
                ],
            ),
            JsonConfigSettingsSource(
                settings_cls=settings_cls,
                json_file=[
                    "secretmanager.json",
                    RELATIVE_CONFIG_BASE_PATH / "config.json",
                    XDG_CONFIG_BASE_PATH / "config.json",
                ],
            ),
            PyprojectTomlConfigSettingsSource(settings_cls),
        )


Settings = SettingsFactory()
