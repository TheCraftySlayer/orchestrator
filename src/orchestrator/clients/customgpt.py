"""Utilities for interacting with the CustomGPT REST API."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib import error, parse, request

class CustomGPTError(RuntimeError):
    """Raised when the CustomGPT API request fails."""


class CustomGPTClient:
    """Minimal client for the CustomGPT REST API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://app.customgpt.ai/api/v1",
        timeout: Optional[float] = 10.0,
    ) -> None:
        if not api_key:
            raise ValueError("An API key is required to talk to CustomGPT.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def api_key(self) -> str:
        """Return the API key used for authentication."""

        return self._api_key

    @property
    def base_url(self) -> str:
        """Return the base URL for the CustomGPT API."""

        return self._base_url

    def get_conversation_messages(
        self,
        project_id: int | str,
        session_id: str,
        *,
        page: int = 1,
        order: str = "desc",
    ) -> Dict[str, Any]:
        """Retrieve messages exchanged in the specified conversation.

        Parameters
        ----------
        project_id:
            The numeric project identifier assigned by CustomGPT.
        session_id:
            The identifier of the conversation whose messages should be
            fetched.
        page:
            Which results page to request. Defaults to 1.
        order:
            Sort order of the messages, either ``"asc"`` or ``"desc"``.

        Returns
        -------
        dict
            The deserialized JSON response returned by the API.

        Raises
        ------
        ValueError
            If an unsupported sort order is supplied.
        CustomGPTError
            If the request fails or the response cannot be parsed.
        """

        if order not in {"asc", "desc"}:
            raise ValueError("order must be either 'asc' or 'desc'.")

        url = self._build_messages_url(project_id, session_id, page=page, order=order)
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._api_key}",
        }

        req = request.Request(url, headers=headers, method="GET")

        try:
            with request.urlopen(req, timeout=self._timeout) as response:  # type: ignore[arg-type]
                payload = response.read()
        except error.HTTPError as exc:  # pragma: no cover - defensive branch
            body = exc.read().decode("utf-8", errors="replace")
            raise CustomGPTError(
                f"CustomGPT API responded with HTTP {exc.code}: {body.strip() or exc.reason}"
            ) from exc
        except error.URLError as exc:  # pragma: no cover - defensive branch
            raise CustomGPTError(f"Failed to reach CustomGPT API: {exc.reason}") from exc

        try:
            decoded = payload.decode("utf-8") if isinstance(payload, bytes) else payload
            data = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CustomGPTError("CustomGPT API returned malformed JSON.") from exc

        if not isinstance(data, dict):
            raise CustomGPTError("Unexpected response type received from CustomGPT API.")

        return data

    def _build_messages_url(
        self,
        project_id: int | str,
        session_id: str,
        *,
        page: int,
        order: str,
    ) -> str:
        """Construct the request URL for retrieving conversation messages."""

        path = f"/projects/{project_id}/conversations/{session_id}/messages"
        params = parse.urlencode({"page": page, "order": order})
        return f"{self._base_url}{path}?{params}"
