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
"""Configuration helpers for the orchestrator service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


@dataclass
class Settings:
    """Runtime configuration loaded from environment variables."""

    customgpt_api_key: str
    customgpt_api_base: str = "https://app.customgpt.ai/api/v1"
    orchestrator_base_url: Optional[str] = None


def _load_settings() -> Settings:
    api_key = os.getenv("CUSTOMGPT_API_KEY")
    if not api_key:
        raise RuntimeError("CUSTOMGPT_API_KEY environment variable is required")

    api_base = os.getenv("CUSTOMGPT_API_BASE", "https://app.customgpt.ai/api/v1")
    orchestrator_base = os.getenv("ORCHESTRATOR_BASE_URL")

    return Settings(
        customgpt_api_key=api_key,
        customgpt_api_base=api_base,
        orchestrator_base_url=orchestrator_base,
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""

    return _load_settings()
