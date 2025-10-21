"""Tests for orchestrator configuration helpers."""

from __future__ import annotations

import pytest

from orchestrator.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Ensure cached settings are cleared between tests."""

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_loads_api_base_from_new_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """CUSTOMGPT_API_BASE takes precedence when both variables are set."""

    monkeypatch.setenv("CUSTOMGPT_API_KEY", "key")
    monkeypatch.setenv("CUSTOMGPT_API_BASE", "https://new.example.com")
    monkeypatch.setenv("CUSTOMGPT_BASE_URL", "https://legacy.example.com")

    settings = get_settings()

    assert isinstance(settings, Settings)
    assert settings.customgpt_api_base == "https://new.example.com"


def test_falls_back_to_legacy_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """CUSTOMGPT_BASE_URL remains supported for backwards compatibility."""

    monkeypatch.setenv("CUSTOMGPT_API_KEY", "key")
    monkeypatch.delenv("CUSTOMGPT_API_BASE", raising=False)
    monkeypatch.setenv("CUSTOMGPT_BASE_URL", "https://legacy.example.com")

    settings = get_settings()

    assert isinstance(settings, Settings)
    assert settings.customgpt_api_base == "https://legacy.example.com"


def test_defaults_to_production_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """When neither variable is set, we fall back to the production CustomGPT base URL."""

    monkeypatch.setenv("CUSTOMGPT_API_KEY", "key")
    monkeypatch.delenv("CUSTOMGPT_API_BASE", raising=False)
    monkeypatch.delenv("CUSTOMGPT_BASE_URL", raising=False)

    settings = get_settings()

    assert isinstance(settings, Settings)
    assert settings.customgpt_api_base == "https://app.customgpt.ai/api/v1"
