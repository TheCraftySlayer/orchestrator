"""Tests for the ``python -m orchestrator.config`` helper."""
from __future__ import annotations

import json

from orchestrator import config


def test_validate_settings_accepts_valid_configuration():
    settings = config.Settings(customgpt_api_key="test", customgpt_api_base="https://example.com")
    assert config.validate_settings(settings) == []


def test_validate_settings_rejects_invalid_urls():
    settings = config.Settings(customgpt_api_key="test", customgpt_api_base="not-a-url")
    errors = config.validate_settings(settings)
    assert "CUSTOMGPT_API_BASE" in " ".join(errors)


def test_main_check_success(monkeypatch, capsys):
    monkeypatch.setenv("CUSTOMGPT_API_KEY", "secret-value")
    monkeypatch.setenv("CUSTOMGPT_API_BASE", "https://app.customgpt.ai/api/v1")

    exit_code = config.main(["--check"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Configuration looks good." in captured.out


def test_main_check_failure(monkeypatch, capsys):
    monkeypatch.delenv("CUSTOMGPT_API_KEY", raising=False)

    exit_code = config.main(["--check"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "CUSTOMGPT_API_KEY environment variable is required" in captured.err


def test_main_show_masks_api_key(monkeypatch, capsys):
    monkeypatch.setenv("CUSTOMGPT_API_KEY", "abcd1234efgh")
    monkeypatch.setenv("CUSTOMGPT_API_BASE", "https://example.com/api")

    exit_code = config.main(["--show"])

    captured = capsys.readouterr()
    assert exit_code == 0

    payload = json.loads(captured.out)
    assert payload["customgpt_api_key"].startswith("abcd")
    assert payload["customgpt_api_key"].endswith("efgh")
    assert set(payload.keys()) >= {"customgpt_api_base", "customgpt_api_key"}

