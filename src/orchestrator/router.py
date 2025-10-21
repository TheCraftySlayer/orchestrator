"""FastAPI routes for the orchestrator service."""
from __future__ import annotations

from typing import Any, Dict, Literal
from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from httpx import HTTPStatusError, RequestError
from pydantic import BaseModel

from orchestrator.agents import BuilderAgent, PlanningAgent, ResearchAgent, ReviewerAgent
from orchestrator.clients.customgpt import (
    CustomGPTClient,
    CustomGPTClientError,
    CustomGPTError,
    CustomGPTServerError,
    get_customgpt_client,
)


class UpdateConversationRequest(BaseModel):
    """Payload used to update an existing CustomGPT conversation."""

    name: str | None = None


class UpdateConversationResponse(BaseModel):
    """Response model for conversation updates."""

    detail: str
    data: dict[str, object] | None = None


router = APIRouter(prefix="/v1")


class ChatMessage(BaseModel):
    """Message exchanged within a conversation."""

    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Incoming payload for the chat orchestration endpoint."""

    conversation_id: str
    messages: list[ChatMessage]
    context: dict[str, Any] | None = None


class ChatStep(BaseModel):
    """Individual agent contribution captured for debugging purposes."""

    agent: str
    output: str


class ChatResponse(BaseModel):
    """Structured response returned by the orchestrator."""

    conversation_id: str
    reply: str
    steps: list[ChatStep]


_RESEARCH_AGENT = ResearchAgent()
_PLANNING_AGENT = PlanningAgent()
_BUILDER_AGENT = BuilderAgent()
_REVIEWER_AGENT = ReviewerAgent()


def _get_latest_user_message(messages: list[ChatMessage]) -> ChatMessage:
    """Return the most recent user-authored message from the conversation history."""

    for message in reversed(messages):
        if message.role == "user":
            return message
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="At least one user message is required to generate a response.",
    )


_ORCHESTRATOR_HEADER = "[ORCHESTRATOR → A.C.E]"
_USER_TEXT_BEGIN = "USER_TEXT_BEGIN"
_USER_TEXT_END = "USER_TEXT_END"


def _extract_orchestrated_text(content: str) -> str:
    """Return the payload from an orchestrator relay envelope if present."""

    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    first_non_blank = next((line for line in lines if line.strip()), "")
    if first_non_blank != _ORCHESTRATOR_HEADER:
        return content

    begin_index = None
    for index, line in enumerate(lines):
        if line.strip() == _USER_TEXT_BEGIN:
            begin_index = index + 1
            break

    if begin_index is None:
        return content

    end_index = None
    for index in range(begin_index, len(lines)):
        if lines[index].strip() == _USER_TEXT_END:
            end_index = index
            break

    extracted_lines = lines[begin_index:end_index]
    extracted_text = "\n".join(extracted_lines).rstrip("\n")

    return extracted_text


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def orchestrate_chat(request: ChatRequest) -> ChatResponse:
    """Coordinate stub agents to produce a multi-step reply."""

    if not request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation history must include at least one message.",
        )

    latest_user_message = _get_latest_user_message(request.messages)
    extracted_content = _extract_orchestrated_text(latest_user_message.content)
    if extracted_content == "":
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)

    latest_user_message = ChatMessage(role=latest_user_message.role, content=extracted_content)

    research_summary = _RESEARCH_AGENT.run(latest_user_message.content)
    plan = _PLANNING_AGENT.run(research_summary)
    draft = _BUILDER_AGENT.run(plan)
    review = _REVIEWER_AGENT.run(draft)

    reply = "\n\n".join([research_summary, plan, draft, review])
    steps = [
        ChatStep(agent="researcher", output=research_summary),
        ChatStep(agent="planner", output=plan),
        ChatStep(agent="builder", output=draft),
        ChatStep(agent="reviewer", output=review),
    ]

    return ChatResponse(conversation_id=request.conversation_id, reply=reply, steps=steps)


_CUSTOMGPT_STATUS_MAP: tuple[tuple[type[CustomGPTError], int], ...] = (
    (CustomGPTClientError, status.HTTP_400_BAD_REQUEST),
    (CustomGPTServerError, status.HTTP_502_BAD_GATEWAY),
    (CustomGPTError, status.HTTP_500_INTERNAL_SERVER_ERROR),
)


def _raise_customgpt_exception(
    exc: CustomGPTError,
    *,
    fallback_messages: Mapping[type[CustomGPTError], str] | None = None,
) -> None:
    """Translate CustomGPT errors into FastAPI HTTP exceptions."""

    fallback_messages = fallback_messages or {}
    for error_type, status_code in _CUSTOMGPT_STATUS_MAP:
        if isinstance(exc, error_type):
            fallback = fallback_messages.get(error_type)
            detail = str(exc) or fallback or str(exc)
            raise HTTPException(status_code=status_code, detail=detail) from exc

    raise exc


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
    except CustomGPTError as exc:
        _raise_customgpt_exception(exc)
    except HTTPStatusError as exc:  # pragma: no cover - compatibility with DummyClient tests
        status_code = exc.response.status_code
        try:
            detail = exc.response.json()
        except ValueError:
            detail = {"detail": exc.response.text}

        if status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
        if status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail) from exc
        if status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
    except RequestError as exc:  # pragma: no cover - compatibility with DummyClient tests
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"detail": str(exc)},
        ) from exc


@router.put(
    "/projects/{project_id}/conversations/{session_id}",
    response_model=UpdateConversationResponse,
    status_code=status.HTTP_200_OK,
)
def update_conversation(
    project_id: str,
    session_id: str,
    request: UpdateConversationRequest,
    client: CustomGPTClient = Depends(get_customgpt_client),
) -> UpdateConversationResponse:
    """Update the metadata for a CustomGPT conversation."""

    try:
        data = client.update_conversation(
            project_id=project_id,
            session_id=session_id,
            name=request.name,
        )
    except CustomGPTError as exc:
        _raise_customgpt_exception(
            exc,
            fallback_messages={
                CustomGPTClientError: "Upstream request failed with a client error.",
                CustomGPTServerError: "Upstream service encountered an error.",
                CustomGPTError: "Unexpected error talking to CustomGPT.",
            },
        )

    return UpdateConversationResponse(detail="Conversation updated.", data=data)


__all__ = [
    "router",
    "list_project_conversations",
    "update_conversation",
    "orchestrate_chat",
]
