from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    discord_token: str = Field(..., alias="DISCORD_TOKEN")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
