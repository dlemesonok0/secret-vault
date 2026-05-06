from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    admin_token: str = "change-me"
    database_url: str = Field(
        default="sqlite:///./data/vault.db",
        validation_alias=AliasChoices("DATABASE_URL", "VAULT_DATABASE_URL"),
    )
    unseal_min_parts: int = 3
    default_wrap_ttl_seconds: int = 60
    max_wrap_ttl_seconds: int = 300
    unwrap_rate_limit_requests: int = 20
    unwrap_rate_limit_window_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VAULT_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
