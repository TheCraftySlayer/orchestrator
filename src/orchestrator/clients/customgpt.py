"""Client for interacting with the CustomGPT REST API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict
from urllib import error, request


class CustomGPTError(Exception):
    """Base error raised for CustomGPT client issues."""


class CustomGPTClientError(CustomGPTError):
    """Raised when the CustomGPT API returns a 4xx response."""


class CustomGPTServerError(CustomGPTError):
    """Raised when the CustomGPT API returns a 5xx response."""


@dataclass
class CustomGPTClient:
    """Simple wrapper around the CustomGPT HTTP API."""

    api_key: str
    base_url: str = "https://app.customgpt.ai/api/v1"
    timeout: float = 10.0

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def update_conversation(
        self, project_id: str, session_id: str, name: str | None
    ) -> Dict[str, Any]:
        """Update the metadata associated with a conversation."""

        url = f"{self.base_url.rstrip('/')}/projects/{project_id}/conversations/{session_id}"
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name

        data = json.dumps(payload).encode("utf-8") if payload else b"{}"
        req = request.Request(
            url,
            data=data,
            headers=self._headers(),
            method="PUT",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                status = response.getcode()
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            if 400 <= exc.code < 500:
                raise CustomGPTClientError(
                    f"CustomGPT rejected the request (status {exc.code})."
                ) from exc
            if exc.code >= 500:
                raise CustomGPTServerError(
                    f"CustomGPT encountered an error (status {exc.code})."
                ) from exc
            raise CustomGPTError(
                f"Unexpected response status {exc.code} from CustomGPT API."
            ) from exc
        except error.URLError as exc:
            raise CustomGPTError("Failed to reach CustomGPT API") from exc

        if 200 <= status < 300:
            if body:
                try:
                    return json.loads(body)
                except json.JSONDecodeError as exc:
                    raise CustomGPTError("Invalid JSON received from CustomGPT API") from exc
            return {}

        if 400 <= status < 500:
            raise CustomGPTClientError(
                f"CustomGPT rejected the request (status {status})."
            )

        if status >= 500:
            raise CustomGPTServerError(
                f"CustomGPT encountered an error (status {status})."
            )

        raise CustomGPTError(f"Unexpected response status {status} from CustomGPT API.")
