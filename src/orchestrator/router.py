"""API routes for the orchestrator service."""
from __future__ import annotations

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from httpx import HTTPStatusError, RequestError

from orchestrator.clients.customgpt import CustomGPTClient, get_customgpt_client

router = APIRouter(prefix="/v1")


@router.get("/projects/{project_id}/conversations", status_code=status.HTTP_200_OK)
def list_project_conversations(
    project_id: str = Path(..., min_length=1),
    page: int = Query(1, ge=1),
    order: Literal["asc", "desc"] = Query("desc"),
    order_by: str = Query("id", min_length=1),
    user_filter: str = Query("all", min_length=1),
    name: str | None = Query(None, min_length=1),
    client: CustomGPTClient = Depends(get_customgpt_client),
) -> Dict[str, Any]:
    """Return a page of conversations for the requested project."""

    try:
        return client.list_conversations(
            project_id,
            page=page,
            order=order,
            order_by=order_by,
            user_filter=user_filter,
            name=name,
        )
    except RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"detail": str(exc)},
        ) from exc
    except HTTPStatusError as exc:  # pragma: no cover - defensive
        status_code = exc.response.status_code
        detail: Dict[str, Any]
        try:
            detail = exc.response.json()
        except ValueError:  # pragma: no cover - fallback when body is not JSON
            detail = {"detail": exc.response.text}

        if status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        if status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        if status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


__all__ = ["router", "list_project_conversations"]
