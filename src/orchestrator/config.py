"""Configuration helpers for the orchestrator service."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    customgpt_api_key: str
    customgpt_api_base: str = "https://app.customgpt.ai/api/v1"
    orchestrator_base_url: str | None = None


def _load_settings() -> Settings:
    """Load configuration from environment variables."""

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


def get_customgpt_headers(api_key: str) -> dict[str, str]:
    """Build HTTP headers for CustomGPT API requests."""

    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


__all__ = ["Settings", "get_settings", "get_customgpt_headers"]
