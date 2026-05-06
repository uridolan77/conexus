"""Pure helpers and HTTP client for admin → adaptation service proxy."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from fastapi import Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.admin_auth_service import AdminSession
from app.services.admin_permissions_service import (
    deployment_roles_from_permissions,
    get_admin_permissions,
)

logger = logging.getLogger(__name__)


def proxy_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"title": title, "detail": detail, "status": status_code},
    )


def adaptation_base_url() -> str | None:
    base = getattr(settings, "adaptation_api_base_url", None)
    if not base:
        return None
    if not isinstance(base, str):
        return None
    base = base.strip()
    if not base:
        return None
    return base.rstrip("/")


def response_from_upstream(upstream: httpx.Response) -> Response:
    content_type = upstream.headers.get("content-type")
    headers: dict[str, str] = {}
    if content_type:
        headers["content-type"] = content_type
    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers)


def idempotency_headers_from_request(request: Request) -> dict[str, str]:
    """Forward Idempotency-Key when present (safe client-generated keys only)."""
    raw = request.headers.get("idempotency-key")
    if raw is None or not str(raw).strip():
        return {}
    return {"Idempotency-Key": str(raw).strip()}


async def proxy_adaptation_request(
    *,
    method: str,
    upstream_path: str,
    request: Request,
    json_body: dict[str, Any] | None = None,
    timeout_seconds: float = 10.0,
    upstream_headers: dict[str, str] | None = None,
) -> Response:
    base = adaptation_base_url()
    if not base:
        return proxy_problem(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            title="Adaptation service is not configured.",
            detail="Set ADAPTATION_API_BASE_URL to enable adaptation BO proxy endpoints.",
        )

    url = f"{base}{upstream_path}"
    params = list(request.query_params.multi_items())
    timeout = httpx.Timeout(timeout_seconds)
    headers = dict(upstream_headers) if upstream_headers else None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(method, url, params=params, json=json_body, headers=headers)
    except httpx.ReadTimeout:
        return proxy_problem(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            title="Adaptation service timed out.",
            detail=f"Timed out waiting for adaptation service after {timeout_seconds:.0f}s.",
        )
    except httpx.ConnectError:
        return proxy_problem(
            status_code=status.HTTP_502_BAD_GATEWAY,
            title="Adaptation service is unavailable.",
            detail="Unable to connect to adaptation service.",
        )
    except httpx.HTTPError as exc:
        return proxy_problem(
            status_code=status.HTTP_502_BAD_GATEWAY,
            title="Adaptation service is unavailable.",
            detail=str(exc),
        )
    except Exception:
        logger.exception("admin_adaptation_proxy_unexpected_error path=%s", upstream_path)
        return proxy_problem(
            status_code=status.HTTP_502_BAD_GATEWAY,
            title="Adaptation proxy error.",
            detail="Unexpected error while proxying to adaptation service.",
        )

    return response_from_upstream(upstream)


async def deployment_identity(
    session: AsyncSession,
    *,
    admin: AdminSession,
) -> tuple[str, list[str]]:
    user_id = (admin.username or admin.admin_user_id or "admin-user").strip() or "admin-user"
    perms = await get_admin_permissions(session, admin=admin)
    return (user_id, deployment_roles_from_permissions(perms))


async def read_deployment_request_json(request: Request) -> dict[str, Any] | JSONResponse:
    """Parse JSON object from deployment POST bodies."""
    try:
        body = await request.body()
        if not body:
            return {}
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return proxy_problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid JSON body.",
            detail="Request body is not valid JSON.",
        )
    except UnicodeDecodeError:
        return proxy_problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid JSON body.",
            detail="Request body is not valid UTF-8.",
        )
    if not isinstance(data, dict):
        return proxy_problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid JSON body.",
            detail="Request body must be a JSON object.",
        )
    return data


def trim_optional_reason(raw: dict[str, Any]) -> None:
    if "reason" not in raw:
        return
    value = raw.get("reason")
    trimmed = (str(value).strip() if value is not None else "").strip()
    if trimmed:
        raw["reason"] = trimmed
    else:
        raw.pop("reason", None)


def strip_browser_identity_and_roles_fields(raw: dict[str, Any]) -> None:
    """Remove browser-supplied identity/role fields (case-insensitive, supports snake_case)."""

    def norm(key: str) -> str:
        return "".join(ch for ch in key.lower() if ch != "_")

    forbidden = {
        "requestedbyuserid",
        "cancelledbyuserid",
        "createdbyuserid",
        "userid",
        "roles",
        "approverroles",
    }

    for k in list(raw.keys()):
        try:
            nk = norm(str(k))
        except Exception:
            continue
        if nk in forbidden:
            raw.pop(k, None)
