"""POST /v1/chat/completions — OpenAI-compatible gateway endpoint.

Goal (docs/04_GATEWAY.md): a client that already speaks the OpenAI Chat
Completions API can swap ``base_url`` and ``api_key`` and keep working.
"""

from __future__ import annotations

import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import AuthenticatedProject, require_project_api_key
from app.db.session import get_session
from app.llm import LLMProvider
from app.llm.dependencies import get_provider
from app.services.gateway_service import (
    GatewayClientError,
    GatewayUpstreamError,
    run_chat_completion,
)

router = APIRouter(prefix="/v1", tags=["gateway"])


class ChatMessageBody(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionsBody(BaseModel):
    model: str = Field(..., min_length=1)
    messages: list[ChatMessageBody] = Field(..., min_length=1)
    max_tokens: int = Field(default=4096, ge=1, le=128_000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class _Choice(BaseModel):
    index: int
    message: ChatMessageBody
    finish_reason: str


class _Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionsResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    provider: str
    fallback_used: bool
    choices: list[_Choice]
    usage: _Usage


@router.post("/chat/completions", response_model=ChatCompletionsResponse)
async def chat_completions(
    body: ChatCompletionsBody,
    auth: Annotated[AuthenticatedProject, Depends(require_project_api_key)],
    session: Annotated[AsyncSession, Depends(get_session)],
    provider: Annotated[LLMProvider, Depends(get_provider)],
) -> ChatCompletionsResponse:
    try:
        response = await run_chat_completion(
            session=session,
            provider=provider,
            project=auth.project,
            api_key=auth.api_key,
            model=body.model,
            messages=[m.model_dump() for m in body.messages],  # type: ignore[arg-type]
            max_tokens=body.max_tokens,
            temperature=body.temperature,
        )
    except GatewayClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except GatewayUpstreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    result = response.result
    return ChatCompletionsResponse(
        id=f"chatcmpl-{response.request_id}",
        created=int(time.time()),
        model=result.model,
        provider=result.provider,
        fallback_used=result.fallback_used,
        choices=[
            _Choice(
                index=0,
                message=ChatMessageBody(role="assistant", content=result.content),
                finish_reason="stop",
            )
        ],
        usage=_Usage(
            prompt_tokens=result.usage.input_tokens,
            completion_tokens=result.usage.output_tokens,
            total_tokens=result.usage.total_tokens,
        ),
    )
