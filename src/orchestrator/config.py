"""Application configuration helpers."""
from __future__ import annotations

from functools import lru_cache

from pydantic import BaseSettings, Field, HttpUrl


class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    customgpt_api_key: str = Field(..., env="CUSTOMGPT_API_KEY")
    customgpt_base_url: HttpUrl = Field(
        "https://app.customgpt.ai", env="CUSTOMGPT_BASE_URL"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


def get_customgpt_headers(api_key: str) -> dict[str, str]:
    """Build HTTP headers for CustomGPT API requests."""

    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
