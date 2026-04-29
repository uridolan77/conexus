"""POST /v1/chat/completions — minimal OpenAI-compatible subset.

This endpoint accepts the small slice of the OpenAI Chat Completions request
shape that Conexus needs in M2: ``model`` + ``messages`` + ``max_tokens`` +
``temperature``. Streaming, tool calls, response_format, logprobs, n>1 etc.
are out of scope. Full compatibility may follow once the gateway has more
production usage.
"""

from __future__ import annotations

import logging
import time
import json
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
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
    run_chat_completion_stream,
)
from app.services.request_log_service import new_request_id
from app.llm.types import ChatMessage

logger = logging.getLogger(__name__)

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

    # OpenAI-compat request fields (accepted, mostly ignored for now).
    stream: bool = False
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    stop: str | list[str] | None = None
    user: str | None = None
    response_format: dict[str, Any] | None = None
    seed: int | None = None
    n: int | None = Field(default=None, ge=1, le=128)
    tools: list[dict[str, Any]] | None = None
    tool_choice: dict[str, Any] | str | None = None
    logprobs: bool | None = None
    top_logprobs: int | None = Field(default=None, ge=0, le=20)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)


def _to_chat_messages(messages: list[ChatMessageBody]) -> list[ChatMessage]:
    return [{"role": m.role, "content": m.content} for m in messages]


def _raise_compat_error(*, code: str, message: str) -> None:
    request_id = new_request_id()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=_error_detail(code, message, request_id),
        headers={REQUEST_ID_HEADER: request_id},
    )


def _validate_compat(body: ChatCompletionsBody) -> None:
    if body.n is not None and body.n != 1:
        _raise_compat_error(
            code="n_not_supported",
            message="Only n=1 is supported.",
        )

    if body.tools is not None or body.tool_choice is not None:
        _raise_compat_error(
            code="tool_calls_not_supported",
            message="Tool calls are not supported yet.",
        )

    if body.logprobs is not None or body.top_logprobs is not None:
        _raise_compat_error(
            code="logprobs_not_supported",
            message="logprobs are not supported yet.",
        )

    if body.response_format is not None:
        rf_type = body.response_format.get("type")
        if rf_type not in (None, "text"):
            _raise_compat_error(
                code="response_format_not_supported",
                message="Only response_format.type='text' is supported.",
            )


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


def _raise_gateway_http(exc: Exception) -> None:
    if isinstance(exc, GatewayClientError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error_detail(exc.code, str(exc), exc.request_id),
            headers={REQUEST_ID_HEADER: exc.request_id},
        ) from exc
    if isinstance(exc, GatewayLimitError):
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
    if isinstance(exc, GatewayUpstreamError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_error_detail(exc.code, str(exc), exc.request_id),
            headers={REQUEST_ID_HEADER: exc.request_id},
        ) from exc
    raise exc


@router.post("/chat/completions", response_model=ChatCompletionsResponse)
async def chat_completions(
    body: ChatCompletionsBody,
    response: Response,
    auth: Annotated[AuthenticatedProject, Depends(require_project_api_key)],
    sessionmaker: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_db_sessionmaker)
    ],
    provider: Annotated[LLMProvider, Depends(get_provider)],
) -> ChatCompletionsResponse | StreamingResponse:
    _validate_compat(body)
    created = int(time.time())
    if body.stream:
        try:
            stream_result = await run_chat_completion_stream(
                sessionmaker=sessionmaker,
                provider=provider,
                project=auth.project,
                api_key=auth.api_key,
                model=body.model,
                messages=_to_chat_messages(body.messages),
                max_tokens=body.max_tokens,
                temperature=body.temperature,
            )
        except (GatewayClientError, GatewayLimitError, GatewayUpstreamError) as exc:
            _raise_gateway_http(exc)

        request_id = stream_result.request_id
        chat_id = f"chatcmpl-{request_id}"

        async def _event_stream():
            sent_role = False
            try:
                async for chunk in stream_result.stream:
                    delta: dict[str, object] = {}
                    if chunk.role_delta and not sent_role:
                        delta["role"] = chunk.role_delta
                        sent_role = True
                    if chunk.content_delta:
                        delta["content"] = chunk.content_delta

                    payload = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": chunk.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": delta,
                                "finish_reason": chunk.finish_reason,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
            except Exception:
                logger.exception(
                    "gateway_stream_interrupted request_id=%s", request_id
                )
                # Best-effort SSE error. The DB log is written by the stream wrapper.
                err_payload = {
                    "error": {
                        "message": "Stream interrupted.",
                        "type": "server_error",
                    }
                }
                yield f"data: {json.dumps(err_payload)}\n\n".encode("utf-8")
            finally:
                yield b"data: [DONE]\n\n"

        return StreamingResponse(
            _event_stream(),
            media_type="text/event-stream",
            headers={REQUEST_ID_HEADER: request_id},
        )

    try:
        result = await run_chat_completion(
            sessionmaker=sessionmaker,
            provider=provider,
            project=auth.project,
            api_key=auth.api_key,
            model=body.model,
            messages=_to_chat_messages(body.messages),
            max_tokens=body.max_tokens,
            temperature=body.temperature,
        )
    except (GatewayClientError, GatewayLimitError, GatewayUpstreamError) as exc:
        _raise_gateway_http(exc)

    chat_result = result.result
    response.headers[REQUEST_ID_HEADER] = result.request_id
    return ChatCompletionsResponse(
        id=f"chatcmpl-{result.request_id}",
        created=created,
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
