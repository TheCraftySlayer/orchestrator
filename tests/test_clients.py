"""Tests for the CustomGPT client."""

import json
from urllib import error

import pytest

from orchestrator.clients.customgpt import (
    CustomGPTClient,
    CustomGPTClientError,
    CustomGPTError,
    CustomGPTServerError,
)


class _MockHTTPResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self._status_code = status_code
        self._payload = payload or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def getcode(self) -> int:
        return self._status_code

    def read(self) -> bytes:
        if self._payload:
            return json.dumps(self._payload).encode("utf-8")
        return b""


def test_update_conversation_success(monkeypatch):
    """The client should return the decoded payload on success."""

    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["data"] = json.loads(req.data.decode("utf-8"))
        captured["headers"] = req.headers
        captured["timeout"] = timeout
        return _MockHTTPResponse(200, {"status": "ok"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = CustomGPTClient(api_key="secret")
    result = client.update_conversation("proj", "sess", name="Demo")

    assert result == {"status": "ok"}
    assert captured["url"].endswith("/projects/proj/conversations/sess")
    assert captured["data"] == {"name": "Demo"}
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_update_conversation_4xx(monkeypatch):
    """A 4xx response should raise a client error."""

    def fake_urlopen(req, timeout):
        raise error.HTTPError(req.full_url, 404, "not found", hdrs=None, fp=None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = CustomGPTClient(api_key="secret")

    with pytest.raises(CustomGPTClientError):
        client.update_conversation("proj", "sess", name=None)


def test_update_conversation_5xx(monkeypatch):
    """A 5xx response should raise a server error."""

    def fake_urlopen(req, timeout):
        raise error.HTTPError(req.full_url, 503, "unavailable", hdrs=None, fp=None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = CustomGPTClient(api_key="secret")

    with pytest.raises(CustomGPTServerError):
        client.update_conversation("proj", "sess", name="Demo")


def test_update_conversation_network_error(monkeypatch):
    """Network errors should surface as a generic client exception."""

    def fake_urlopen(req, timeout):
        raise error.URLError("boom")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = CustomGPTClient(api_key="secret")

    with pytest.raises(CustomGPTError):
        client.update_conversation("proj", "sess", name="Demo")
