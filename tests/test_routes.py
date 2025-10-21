"""Route-level tests for the orchestrator API."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterable

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import HTTPStatusError, Request, RequestError, Response

from orchestrator.main import app
from orchestrator.clients import customgpt


@pytest.fixture()
def client() -> Iterable[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@contextmanager
def override_client(mock_client):
    def _dependency_override():
        yield mock_client

    app.dependency_overrides[customgpt.get_customgpt_client] = _dependency_override
    try:
        yield
    finally:
        app.dependency_overrides.pop(customgpt.get_customgpt_client, None)


class DummyClient:
    def __init__(self, response_payload: Dict[str, Any] | None = None):
        self.calls: list[Dict[str, Any]] = []
        self.response_payload = response_payload or {
            "data": [{"id": "conv-1", "name": "Sample conversation"}],
            "meta": {"page": 1},
        }

    def list_conversations(self, project_id: str, **params: Any) -> Dict[str, Any]:
        self.calls.append({"project_id": project_id, **params})
        return self.response_payload

    def close(self) -> None:  # pragma: no cover - compatibility with dependency
        return None


def test_list_conversations_success(client: TestClient):
    mock_client = DummyClient()
    with override_client(mock_client):
        response = client.get("/v1/projects/proj-123/conversations")
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["data"][0]["id"] == "conv-1"
    assert mock_client.calls[0]["project_id"] == "proj-123"


def test_list_conversations_with_pagination(client: TestClient):
    mock_client = DummyClient(response_payload={"data": [], "meta": {"page": 3}})
    with override_client(mock_client):
        response = client.get("/v1/projects/proj-123/conversations", params={"page": 3})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["meta"]["page"] == 3
    assert mock_client.calls[0]["page"] == 3


def test_list_conversations_with_filters(client: TestClient):
    mock_client = DummyClient()
    params = {"order": "asc", "order_by": "updated_at", "user_filter": "mine", "name": "weekly"}
    with override_client(mock_client):
        response = client.get("/v1/projects/proj-123/conversations", params=params)
    assert response.status_code == status.HTTP_200_OK
    for key, value in params.items():
        assert mock_client.calls[0][key] == value


@pytest.mark.parametrize(
    "status_code",
    [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND],
)
def test_list_conversations_error_mapping(client: TestClient, status_code: int):
    error_response = Response(
        status_code,
        request=Request("GET", "https://app.customgpt.ai"),
        json={"detail": "error"},
    )
    error = HTTPStatusError("error", request=error_response.request, response=error_response)

    class ErrorClient(DummyClient):
        def list_conversations(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
            raise error

    with override_client(ErrorClient()):
        response = client.get("/v1/projects/proj-123/conversations")
    assert response.status_code == status_code
    assert response.json() == {"detail": {"detail": "error"}}


def test_list_conversations_server_error_translates_to_bad_gateway(client: TestClient):
    error_response = Response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        request=Request("GET", "https://app.customgpt.ai"),
        json={"detail": "server error"},
    )
    error = HTTPStatusError(
        "server error", request=error_response.request, response=error_response
    )

    class ErrorClient(DummyClient):
        def list_conversations(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
            raise error

    with override_client(ErrorClient()):
        response = client.get("/v1/projects/proj-123/conversations")
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json() == {"detail": {"detail": "server error"}}


def test_list_conversations_network_error_results_in_bad_gateway(client: TestClient):
    class ErrorClient(DummyClient):
        def list_conversations(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
            raise RequestError("network", request=Request("GET", "https://app.customgpt.ai"))

    with override_client(ErrorClient()):
        response = client.get("/v1/projects/proj-123/conversations")
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json() == {"detail": {"detail": "network"}}


def test_orchestrate_chat_returns_agent_steps(client: TestClient):
    payload = {
        "conversation_id": "conv-123",
        "messages": [
            {"role": "user", "content": "Explain the zoning rules for residential areas."}
        ],
    }

    response = client.post("/v1/chat", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["conversation_id"] == "conv-123"
    assert len(data["steps"]) == 4
    assert data["steps"][0]["agent"] == "researcher"
    assert "Researching" in data["steps"][0]["output"]
    assert "Review" in data["reply"]


def test_orchestrate_chat_requires_user_message(client: TestClient):
    payload = {
        "conversation_id": "conv-456",
        "messages": [{"role": "assistant", "content": "How can I assist?"}],
    }

    response = client.post("/v1/chat", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "At least one user message is required to generate a response."


def test_orchestrate_chat_unwraps_orchestrator_payload(client: TestClient):
    payload = {
        "conversation_id": "conv-789",
        "messages": [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "[ORCHESTRATOR → A.C.E]",
                        "AGENT_ID: 37400",
                        "CONVERSATION_ID: abc123",
                        "",
                        "USER_TEXT_BEGIN",
                        "How much is the head of family exemption?",
                        "USER_TEXT_END",
                    ]
                ),
            }
        ],
    }

    response = client.post("/v1/chat", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    research_step = data["steps"][0]
    assert research_step["agent"] == "researcher"
    assert research_step["output"].endswith("How much is the head of family exemption?")


def test_orchestrate_chat_returns_no_content_for_empty_orchestrator_payload(client: TestClient):
    payload = {
        "conversation_id": "conv-101",
        "messages": [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "[ORCHESTRATOR → A.C.E]",
                        "USER_TEXT_BEGIN",
                        "USER_TEXT_END",
                    ]
                ),
            }
        ],
    }

    response = client.post("/v1/chat", json=payload)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_orchestrate_chat_handles_leading_whitespace_in_header(client: TestClient):
    payload = {
        "conversation_id": "conv-202",
        "messages": [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "   [ORCHESTRATOR → A.C.E]",
                        "USER_TEXT_BEGIN",
                        "Hello",
                        "USER_TEXT_END",
                    ]
                ),
            }
        ],
    }

    response = client.post("/v1/chat", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["steps"][0]["output"].endswith("Hello")


def test_orchestrate_chat_missing_user_text_begin_returns_no_content(client: TestClient):
    payload = {
        "conversation_id": "conv-303",
        "messages": [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "[ORCHESTRATOR → A.C.E]",
                        "Some instructions",
                        "USER_TEXT_END",
                    ]
                ),
            }
        ],
    }

    response = client.post("/v1/chat", json=payload)

    assert response.status_code == status.HTTP_204_NO_CONTENT
