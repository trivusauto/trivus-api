from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 10080
    n8n_bulk_send_webhook_url: str | None = None
    n8n_token: str = "dev-n8n-token"
    n8n_interest_webhook_url: str | None = None
    billing_gateway_enabled: bool = False
    billing_token: str = "dev-billing-token"
    meta_enabled: bool = False
    meta_access_token: str = ""
    meta_token: str = "dev-meta-token"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
