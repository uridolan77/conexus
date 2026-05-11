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
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import AuthenticatedProject, require_project_api_key
from app.db.session import get_db_sessionmaker
from app.llm import LLMProvider
from app.llm.dependencies import get_provider
from app.schemas.openai_compat import (
    ChatCompletionsRequest as ChatCompletionsBody,
    ChatCompletionsResponse,
    ChatMessageBody,
)
from app.services.gateway_service import (
    GatewayClientError,
    GatewayConflictError,
    GatewayLimitError,
    GatewayUpstreamError,
    run_chat_completion,
    run_chat_completion_stream,
)
from app.services.request_log_service import is_valid_client_request_id, new_request_id
from app.llm.types import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["gateway"])

REQUEST_ID_HEADER = "X-Conexus-Request-Id"


def _to_chat_messages(messages: list[ChatMessageBody]) -> list[ChatMessage]:
    return [{"role": m.role, "content": m.content} for m in messages]


def _compat_error_request_id(client_request_id: str | None) -> str:
    if client_request_id is not None:
        return client_request_id
    return new_request_id()


def _raise_compat_error(
    *, code: str, message: str, client_request_id: str | None
) -> None:
    request_id = _compat_error_request_id(client_request_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=_error_detail(code, message, request_id),
        headers={REQUEST_ID_HEADER: request_id},
    )


def _validate_compat(body: ChatCompletionsBody, *, client_request_id: str | None) -> None:
    if body.n is not None and body.n != 1:
        _raise_compat_error(
            code="n_not_supported",
            message="Only n=1 is supported.",
            client_request_id=client_request_id,
        )

    if body.tools is not None or body.tool_choice is not None:
        _raise_compat_error(
            code="tool_calls_not_supported",
            message="Tool calls are not supported yet.",
            client_request_id=client_request_id,
        )

    if body.logprobs is not None or body.top_logprobs is not None:
        _raise_compat_error(
            code="logprobs_not_supported",
            message="logprobs are not supported yet.",
            client_request_id=client_request_id,
        )

    if body.response_format is not None:
        rf_type = body.response_format.get("type")
        if rf_type not in (None, "text"):
            _raise_compat_error(
                code="response_format_not_supported",
                message="Only response_format.type='text' is supported.",
                client_request_id=client_request_id,
            )


def _error_detail(code: str, message: str, request_id: str) -> dict[str, object]:
    return {"code": code, "message": message, "request_id": request_id}


def _sse_error_payload(*, exc: Exception | None, request_id: str) -> dict[str, object]:
    msg = getattr(exc, "message", None) if exc is not None else None
    message = str(msg) if msg else (str(exc) if exc is not None else "Stream interrupted.")
    if isinstance(exc, GatewayClientError):
        return {
            "error": {
                "type": "client_error",
                "code": exc.code,
                "message": message,
                "request_id": request_id,
            }
        }
    if isinstance(exc, GatewayLimitError):
        return {
            "error": {
                "type": "rate_limit_error",
                "code": exc.code,
                "message": message,
                "request_id": request_id,
                "limit_type": exc.limit_type,
                "current_value": exc.current_value,
                "limit_value": exc.limit_value,
                "window": exc.window,
                "reset_at": exc.reset_at.isoformat() if exc.reset_at is not None else None,
            }
        }
    if isinstance(exc, GatewayUpstreamError):
        return {
            "error": {
                "type": "upstream_error",
                "code": exc.code,
                "message": message,
                "request_id": request_id,
            }
        }
    return {
        "error": {
            "type": "server_error",
            "message": "Stream interrupted.",
            "request_id": request_id,
        }
    }


def register_gateway_exception_handlers(app: FastAPI) -> None:
    """Map gateway domain errors to the same JSON bodies as legacy HTTPException paths."""

    @app.exception_handler(GatewayConflictError)
    async def _gateway_conflict_error(_request: Request, exc: GatewayConflictError) -> Response:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": _error_detail(exc.code, exc.message, exc.request_id)},
            headers={REQUEST_ID_HEADER: exc.request_id},
        )

    @app.exception_handler(GatewayClientError)
    async def _gateway_client_error(_request: Request, exc: GatewayClientError) -> Response:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": _error_detail(exc.code, exc.message, exc.request_id)},
            headers={REQUEST_ID_HEADER: exc.request_id},
        )

    @app.exception_handler(GatewayLimitError)
    async def _gateway_limit_error(_request: Request, exc: GatewayLimitError) -> Response:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": {
                    **_error_detail(exc.code, exc.message, exc.request_id),
                    "limit_type": exc.limit_type,
                    "current_value": exc.current_value,
                    "limit_value": exc.limit_value,
                    "window": exc.window,
                    "reset_at": exc.reset_at.isoformat() if exc.reset_at is not None else None,
                }
            },
            headers={REQUEST_ID_HEADER: exc.request_id},
        )

    @app.exception_handler(GatewayUpstreamError)
    async def _gateway_upstream_error(_request: Request, exc: GatewayUpstreamError) -> Response:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": _error_detail(exc.code, exc.message, exc.request_id)},
            headers={REQUEST_ID_HEADER: exc.request_id},
        )


@router.post("/chat/completions", response_model=ChatCompletionsResponse)
async def chat_completions(
    body: ChatCompletionsBody,
    response: Response,
    request: Request,
    auth: Annotated[AuthenticatedProject, Depends(require_project_api_key)],
    sessionmaker: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_db_sessionmaker)
    ],
    provider: Annotated[LLMProvider, Depends(get_provider)],
) -> ChatCompletionsResponse | StreamingResponse:
    raw_header = request.headers.get(REQUEST_ID_HEADER)
    if raw_header is not None and raw_header.strip():
        candidate = raw_header.strip()
        if not is_valid_client_request_id(candidate):
            err_rid = new_request_id()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_error_detail(
                    "invalid_conexus_request_id",
                    "X-Conexus-Request-Id must be 1-64 characters from [A-Za-z0-9_-].",
                    err_rid,
                ),
                headers={REQUEST_ID_HEADER: err_rid},
            )
        client_request_id = candidate
    else:
        client_request_id = None

    _validate_compat(body, client_request_id=client_request_id)
    created = int(time.time())
    domain_key = request.headers.get("X-Conexus-Domain-Key")
    explicit_gateway_profile_id = request.headers.get("X-Conexus-Gateway-Profile-Id") or request.headers.get(
        "X-Conexus-Adapter-Profile-Id"
    )
    if body.stream:
        stream_result = await run_chat_completion_stream(
            sessionmaker=sessionmaker,
            provider=provider,
            project=auth.project,
            api_key=auth.api_key,
            model=body.model,
            messages=_to_chat_messages(body.messages),
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            domain_key=domain_key,
            explicit_gateway_profile_id=explicit_gateway_profile_id,
            client_request_id=client_request_id,
        )

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
            except Exception as exc:
                logger.exception(
                    "gateway_stream_interrupted request_id=%s", request_id
                )
                # Best-effort SSE error. The DB log is written by the stream wrapper.
                err_payload = _sse_error_payload(exc=exc, request_id=request_id)
                yield f"data: {json.dumps(err_payload)}\n\n".encode("utf-8")
            finally:
                yield b"data: [DONE]\n\n"

        return StreamingResponse(
            _event_stream(),
            media_type="text/event-stream",
            headers={REQUEST_ID_HEADER: request_id},
        )

    result = await run_chat_completion(
        sessionmaker=sessionmaker,
        provider=provider,
        project=auth.project,
        api_key=auth.api_key,
        model=body.model,
        messages=_to_chat_messages(body.messages),
        max_tokens=body.max_tokens,
        temperature=body.temperature,
        domain_key=domain_key,
        explicit_gateway_profile_id=explicit_gateway_profile_id,
        client_request_id=client_request_id,
    )

    chat_result = result.result
    response.headers[REQUEST_ID_HEADER] = result.request_id
    return ChatCompletionsResponse(
        id=f"chatcmpl-{result.request_id}",
        created=created,
        model=chat_result.model,
        provider=chat_result.provider,
        fallback_used=chat_result.fallback_used,
        request_id=result.request_id,
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": chat_result.content},
                "finish_reason": "stop",
            }
        ],
        usage={
            "prompt_tokens": chat_result.usage.input_tokens,
            "completion_tokens": chat_result.usage.output_tokens,
            "total_tokens": chat_result.usage.total_tokens,
        },
    )
