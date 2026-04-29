"""POST /v1/chat/completions — minimal OpenAI-compatible subset.

This endpoint accepts the small slice of the OpenAI Chat Completions request
shape that Conexus needs in M2: ``model`` + ``messages`` + ``max_tokens`` +
``temperature``. Streaming, tool calls, response_format, logprobs, n>1 etc.
are out of scope. Full compatibility may follow once the gateway has more
production usage.
"""

from __future__ import annotations

import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import AuthenticatedProject, require_project_api_key
from app.db.session import get_db_sessionmaker
from app.llm import LLMProvider
from app.llm.dependencies import get_provider
from app.services.gateway_service import (
    GatewayClientError,
    GatewayLimitError,
    GatewayUpstreamError,
    run_chat_completion,
)

router = APIRouter(prefix="/v1", tags=["gateway"])

REQUEST_ID_HEADER = "X-Conexus-Request-Id"


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


def _error_detail(code: str, message: str, request_id: str) -> dict[str, object]:
    return {"code": code, "message": message, "request_id": request_id}


@router.post("/chat/completions", response_model=ChatCompletionsResponse)
async def chat_completions(
    body: ChatCompletionsBody,
    response: Response,
    auth: Annotated[AuthenticatedProject, Depends(require_project_api_key)],
    sessionmaker: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_db_sessionmaker)
    ],
    provider: Annotated[LLMProvider, Depends(get_provider)],
) -> ChatCompletionsResponse:
    try:
        result = await run_chat_completion(
            sessionmaker=sessionmaker,
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
            detail=_error_detail(exc.code, str(exc), exc.request_id),
            headers={REQUEST_ID_HEADER: exc.request_id},
        ) from exc
    except GatewayLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                **_error_detail(exc.code, str(exc), exc.request_id),
                "limit_type": exc.limit_type,
                "current_value": exc.current_value,
                "limit_value": exc.limit_value,
                "window": exc.window,
                "reset_at": exc.reset_at.isoformat() if exc.reset_at is not None else None,
            },
            headers={REQUEST_ID_HEADER: exc.request_id},
        ) from exc
    except GatewayUpstreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_error_detail(exc.code, str(exc), exc.request_id),
            headers={REQUEST_ID_HEADER: exc.request_id},
        ) from exc

    chat_result = result.result
    response.headers[REQUEST_ID_HEADER] = result.request_id
    return ChatCompletionsResponse(
        id=f"chatcmpl-{result.request_id}",
        created=int(time.time()),
        model=chat_result.model,
        provider=chat_result.provider,
        fallback_used=chat_result.fallback_used,
        choices=[
            _Choice(
                index=0,
                message=ChatMessageBody(role="assistant", content=chat_result.content),
                finish_reason="stop",
            )
        ],
        usage=_Usage(
            prompt_tokens=chat_result.usage.input_tokens,
            completion_tokens=chat_result.usage.output_tokens,
            total_tokens=chat_result.usage.total_tokens,
        ),
    )
