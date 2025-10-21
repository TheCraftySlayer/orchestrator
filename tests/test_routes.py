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
