"""FastAPI routes for the orchestrator service."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .clients.customgpt import (
    CustomGPTClient,
    CustomGPTClientError,
    CustomGPTError,
    CustomGPTServerError,
)
from .config import Settings, get_settings


class UpdateConversationRequest(BaseModel):
    """Payload used to update an existing CustomGPT conversation."""

    name: str | None = None


class UpdateConversationResponse(BaseModel):
    """Response model for conversation updates."""

    detail: str
    data: dict[str, object] | None = None


router = APIRouter(prefix="/v1")


def _get_client(settings: Settings = Depends(get_settings)) -> CustomGPTClient:
    return CustomGPTClient(api_key=settings.customgpt_api_key, base_url=settings.customgpt_api_base)


@router.put(
    "/projects/{project_id}/conversations/{session_id}",
    response_model=UpdateConversationResponse,
    status_code=status.HTTP_200_OK,
)
def update_conversation(
    project_id: str,
    session_id: str,
    request: UpdateConversationRequest,
    client: CustomGPTClient = Depends(_get_client),
) -> UpdateConversationResponse:
    """Update the metadata for a CustomGPT conversation."""

    try:
        data = client.update_conversation(
            project_id=project_id, session_id=session_id, name=request.name
        )
    except CustomGPTClientError as exc:  # 4xx errors from upstream
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc) or "Upstream request failed with a client error.",
        ) from exc
    except CustomGPTServerError as exc:  # 5xx errors
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "Upstream service encountered an error.",
        ) from exc
    except CustomGPTError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc) or "Unexpected error talking to CustomGPT.",
        ) from exc

    return UpdateConversationResponse(detail="Conversation updated.", data=data)
