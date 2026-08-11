from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    phulax_env: str = "dev"
    gateway_signing_key: str = "fake-dev-key-change-me-not-a-secret-0001"
    control_plane_url: str = "http://127.0.0.1:8000"
    token_audience: str = "phulax-gateway"


@lru_cache
def get_settings() -> Settings:
    return Settings()
