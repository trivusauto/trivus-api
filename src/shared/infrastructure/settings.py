from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 10080


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
