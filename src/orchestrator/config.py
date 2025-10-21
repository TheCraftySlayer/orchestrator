"""Configuration helpers for the orchestrator service."""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Sequence
from urllib.parse import urlparse


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


def validate_settings(settings: Settings) -> list[str]:
    """Return validation errors for the provided settings."""

    errors: list[str] = []
    if not settings.customgpt_api_key.strip():
        errors.append("CUSTOMGPT_API_KEY must not be empty.")

    if not _is_valid_url(settings.customgpt_api_base):
        errors.append("CUSTOMGPT_API_BASE must be an absolute URL (e.g. https://example.com/api).")

    if settings.orchestrator_base_url and not _is_valid_url(settings.orchestrator_base_url):
        errors.append(
            "ORCHESTRATOR_BASE_URL must be an absolute URL when provided (e.g. http://localhost:8000)."
        )

    return errors


def _is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)


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


def _mask_secret(secret: str) -> str:
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


def _format_settings(settings: Settings) -> str:
    masked = asdict(settings)
    masked["customgpt_api_key"] = _mask_secret(masked["customgpt_api_key"])
    return json.dumps(masked, indent=2, sort_keys=True)


def _load_settings_for_cli() -> tuple[Settings | None, list[str]]:
    try:
        settings = _load_settings()
    except RuntimeError:
        return None, ["CUSTOMGPT_API_KEY environment variable is required"]
    return settings, validate_settings(settings)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for ``python -m orchestrator.config``."""

    parser = argparse.ArgumentParser(
        description="Inspect and validate orchestrator environment configuration.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate required environment variables and report any issues.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Print the current configuration with sensitive values masked.",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    settings, errors = _load_settings_for_cli()
    exit_code = 0 if not errors else 1

    if args.show and settings is not None:
        print(_format_settings(settings))
    elif args.show and settings is None:
        exit_code = 1

    if args.check:
        if errors:
            print("Configuration issues detected:", file=sys.stderr)
            for message in errors:
                print(f"- {message}", file=sys.stderr)
        else:
            print("Configuration looks good.")

    if not args.check and not args.show:
        parser.print_help()
        return exit_code

    return exit_code


__all__ = [
    "Settings",
    "get_settings",
    "get_customgpt_headers",
    "validate_settings",
    "main",
]


if __name__ == "__main__":  # pragma: no cover - exercised via integration
    raise SystemExit(main())
