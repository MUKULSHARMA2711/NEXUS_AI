from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXUS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NEXUS"
    app_description: str = "AI Engineering Intelligence Platform"
    app_version: str = "0.1.0"
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
