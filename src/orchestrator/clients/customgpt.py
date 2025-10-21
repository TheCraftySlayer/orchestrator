"""Client for interacting with the CustomGPT API."""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from orchestrator.config import get_customgpt_headers, get_settings


class CustomGPTClient:
    """A lightweight HTTP client wrapper around CustomGPT endpoints."""

    def __init__(self, *, api_key: Optional[str] = None, base_url: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.customgpt_api_key
        self.base_url = base_url or str(settings.customgpt_base_url).rstrip("/")
        self._session = httpx.Client()

    def list_conversations(
        self,
        project_id: str,
        *,
        page: int = 1,
        order: str = "desc",
        order_by: str = "id",
        user_filter: str = "all",
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch conversations for the given project."""

        url = f"{self.base_url}/api/v1/projects/{project_id}/conversations"
        params: Dict[str, Any] = {
            "page": page,
            "order": order,
            "order_by": order_by,
            "user_filter": user_filter,
        }
        if name is not None:
            params["name"] = name

        headers = get_customgpt_headers(self.api_key)
        response = self._session.get(url, headers=headers, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the underlying HTTP session."""

        self._session.close()


def get_customgpt_client() -> CustomGPTClient:
    """Dependency provider for FastAPI routes."""

    client = CustomGPTClient()
    try:
        yield client
    finally:
        client.close()
