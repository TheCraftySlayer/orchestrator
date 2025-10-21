"""Top-level package for the CustomGPT Orchestrator service."""

__all__ = [
    "config",
    "main",
    "router",
]
"""Orchestrator package initialization."""

from .config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
"""Orchestrator package for interacting with CustomGPT."""

from .clients.customgpt import CustomGPTClient, CustomGPTError

__all__ = ["CustomGPTClient", "CustomGPTError"]
