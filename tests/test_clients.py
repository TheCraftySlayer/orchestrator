"""Tests for the CustomGPT client using the HTTPX transport layer."""

from __future__ import annotations

import json

import httpx
import pytest

from orchestrator.clients.customgpt import (
    CustomGPTClient,
    CustomGPTClientError,
    CustomGPTError,
    CustomGPTServerError,
)


def _make_client(handler):
    """Create a client that routes requests through the provided handler."""

    transport = httpx.MockTransport(handler)
    httpx_client = httpx.Client(base_url="https://app.customgpt.ai/api/v1", transport=transport)
    client = CustomGPTClient("secret", client=httpx_client)
    return client, httpx_client


def test_update_conversation_success():
    """The client should return the decoded payload on success."""

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content.decode("utf-8"))
        captured["headers"] = {k.lower(): v for k, v in request.headers.items()}
        return httpx.Response(200, json={"status": "ok"})

    client, httpx_client = _make_client(handler)
    try:
        result = client.update_conversation("proj", "sess", name="Demo")
    finally:
        httpx_client.close()

    assert result == {"status": "ok"}
    assert captured["url"].endswith("/projects/proj/conversations/sess")
    assert captured["json"] == {"name": "Demo"}
    assert captured["headers"]["authorization"] == "Bearer secret"


def test_update_conversation_4xx():
    """A 4xx response should raise a client error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    client, httpx_client = _make_client(handler)
    with httpx_client:
        with pytest.raises(CustomGPTClientError):
            client.update_conversation("proj", "sess", name=None)


def test_update_conversation_5xx():
    """A 5xx response should raise a server error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "unavailable"})

    client, httpx_client = _make_client(handler)
    with httpx_client:
        with pytest.raises(CustomGPTServerError):
            client.update_conversation("proj", "sess", name="Demo")


def test_update_conversation_network_error(monkeypatch):
    """Network errors should surface as a generic client exception."""

    client = CustomGPTClient("secret")

    def raise_error(*args, **kwargs):  # pragma: no cover - triggered in test
        raise httpx.RequestError("boom", request=httpx.Request("GET", "http://test"))

    monkeypatch.setattr(client._client, "request", raise_error)  # type: ignore[attr-defined]

    with pytest.raises(CustomGPTError):
        client.update_conversation("proj", "sess", name="Demo")
    client.close()
