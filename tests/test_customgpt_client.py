from __future__ import annotations

import httpx
import pytest

from orchestrator.clients.customgpt import CustomGPTClient, CustomGPTError


def _make_client(handler):
    transport = httpx.MockTransport(handler)
    httpx_client = httpx.Client(base_url="https://app.customgpt.ai/api/v1", transport=transport)
    return CustomGPTClient("test-key", client=httpx_client), httpx_client


def test_build_messages_request_and_query_params():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"messages": []})

    client, httpx_client = _make_client(handler)
    with httpx_client:
        data = client.get_conversation_messages(42, "session-1", page=2, order="asc")

    assert data == {"messages": []}
    assert captured["url"].endswith("/projects/42/conversations/session-1/messages?page=2&order=asc")


def test_get_conversation_messages_invalid_order():
    client = CustomGPTClient("test-key")
    with pytest.raises(ValueError):
        client.get_conversation_messages(1, "abc", order="invalid")
    client.close()


def test_get_conversation_messages_non_dict_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["unexpected"])

    client, httpx_client = _make_client(handler)
    with httpx_client:
        with pytest.raises(CustomGPTError):
            client.get_conversation_messages(1, "abc")
