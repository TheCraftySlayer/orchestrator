"""Client utilities for interacting with the CustomGPT REST API."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Dict, Optional

import httpx

from orchestrator.config import get_customgpt_headers, get_settings


class CustomGPTError(RuntimeError):
    """Raised when the CustomGPT API request fails."""


class CustomGPTClientError(CustomGPTError):
    """Raised when the CustomGPT API returns a 4xx response."""


class CustomGPTServerError(CustomGPTError):
    """Raised when the CustomGPT API returns a 5xx response."""


class CustomGPTClient:
    """HTTP client for the CustomGPT REST API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://app.customgpt.ai/api/v1",
        timeout: Optional[float] = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("An API key is required to talk to CustomGPT.")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        if client is None:
            self._client = httpx.Client(base_url=self._base_url, timeout=timeout)
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    @property
    def api_key(self) -> str:
        """Return the API key used for authentication."""

        return self._api_key

    @property
    def base_url(self) -> str:
        """Return the base URL for the CustomGPT API."""

        return self._base_url

    def close(self) -> None:
        """Close the underlying HTTP client if we created it."""

        if self._owns_client:
            self._client.close()

    def list_conversations(
        self,
        project_id: str | int,
        *,
        page: int = 1,
        order: str = "desc",
        order_by: str = "id",
        user_filter: str = "all",
        name: str | None = None,
    ) -> Dict[str, Any]:
        """Fetch conversations for the given project."""

        params: Dict[str, Any] = {
            "page": page,
            "order": order,
            "orderBy": order_by,
            "userFilter": user_filter,
        }
        if name is not None:
            params["name"] = name

        return self._request(
            "GET",
            f"/projects/{project_id}/conversations",
            params=params,
        )

    def update_conversation(
        self,
        project_id: str | int,
        session_id: str,
        *,
        name: str | None = None,
    ) -> Dict[str, Any]:
        """Update the metadata associated with a conversation."""

        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name

        return self._request(
            "PUT",
            f"/projects/{project_id}/conversations/{session_id}",
            json=payload or None,
        )

    def get_conversation_messages(
        self,
        project_id: str | int,
        session_id: str,
        *,
        page: int = 1,
        order: str = "desc",
    ) -> Dict[str, Any]:
        """Retrieve messages exchanged in the specified conversation."""

        if order not in {"asc", "desc"}:
            raise ValueError("order must be either 'asc' or 'desc'.")

        params = {"page": page, "order": order}
        return self._request(
            "GET",
            f"/projects/{project_id}/conversations/{session_id}/messages",
            params=params,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, Any] | None = None,
        json: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        headers = get_customgpt_headers(self._api_key)
        try:
            response = self._client.request(
                method,
                path,
                headers=headers,
                params=params,
                json=json,
            )
        except httpx.RequestError as exc:  # pragma: no cover - network failure
            raise CustomGPTError(f"Failed to reach CustomGPT API: {exc!s}") from exc

        if 200 <= response.status_code < 300:
            if not response.content:
                return {}
            try:
                data = response.json()
            except ValueError as exc:  # pragma: no cover - defensive
                raise CustomGPTError("CustomGPT API returned malformed JSON.") from exc
            if not isinstance(data, dict):
                raise CustomGPTError("Unexpected response type received from CustomGPT API.")
            return data

        detail = response.text.strip() or response.reason_phrase
        if 400 <= response.status_code < 500:
            raise CustomGPTClientError(
                f"CustomGPT rejected the request (status {response.status_code}): {detail}"
            )
        if response.status_code >= 500:
            raise CustomGPTServerError(
                f"CustomGPT encountered an error (status {response.status_code}): {detail}"
            )
        raise CustomGPTError(
            f"Unexpected response status {response.status_code} from CustomGPT API."
        )


def get_customgpt_client() -> Iterator[CustomGPTClient]:
    """Dependency provider for FastAPI routes."""

    settings = get_settings()
    client = CustomGPTClient(
        api_key=settings.customgpt_api_key,
        base_url=settings.customgpt_api_base,
    )
    try:
        yield client
    finally:
        client.close()


__all__ = [
    "CustomGPTClient",
    "CustomGPTError",
    "CustomGPTClientError",
    "CustomGPTServerError",
    "get_customgpt_client",
]
