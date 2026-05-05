"""Admin proxy endpoints for the adaptation service.

This module intentionally exposes only a small, BO-shaped surface area.
The browser must never call the adaptation service directly.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.admin_auth import get_admin_session
from app.core.config import settings
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
from app.services.admin_permissions_service import (
    ADAPTATION_APPROVE,
    ADAPTATION_OPERATE,
    ADAPTATION_PUBLISH,
    ADAPTATION_ROLLBACK,
    ADAPTATION_VIEW,
    deployment_roles_from_permissions,
    get_admin_permissions,
    require_adaptation_permission,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/adaptation", tags=["admin"])


def _problem(
    *,
    status_code: int,
    title: str,
    detail: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"title": title, "detail": detail, "status": status_code},
    )


def _adaptation_base_url() -> str | None:
    base = getattr(settings, "adaptation_api_base_url", None)
    if not base:
        return None
    if not isinstance(base, str):
        return None
    base = base.strip()
    if not base:
        return None
    return base.rstrip("/")


def _response_from_upstream(upstream: httpx.Response) -> Response:
    content_type = upstream.headers.get("content-type")
    headers: dict[str, str] = {}
    if content_type:
        headers["content-type"] = content_type
    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers)


def _idempotency_headers_from_request(request: Request) -> dict[str, str]:
    """Forward Idempotency-Key from the incoming request when present (safe client-generated keys only)."""
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
    base = _adaptation_base_url()
    if not base:
        return _problem(
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
        return _problem(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            title="Adaptation service timed out.",
            detail=f"Timed out waiting for adaptation service after {timeout_seconds:.0f}s.",
        )
    except httpx.ConnectError:
        return _problem(
            status_code=status.HTTP_502_BAD_GATEWAY,
            title="Adaptation service is unavailable.",
            detail="Unable to connect to adaptation service.",
        )
    except httpx.HTTPError as exc:
        # Covers other transport-level issues without leaking a 500.
        return _problem(
            status_code=status.HTTP_502_BAD_GATEWAY,
            title="Adaptation service is unavailable.",
            detail=str(exc),
        )
    except Exception:
        logger.exception("admin_adaptation_proxy_unexpected_error path=%s", upstream_path)
        return _problem(
            status_code=status.HTTP_502_BAD_GATEWAY,
            title="Adaptation proxy error.",
            detail="Unexpected error while proxying to adaptation service.",
        )

    return _response_from_upstream(upstream)


async def _deployment_identity(
    session: AsyncSession,
    *,
    admin: AdminSession,
) -> tuple[str, list[str]]:
    user_id = (admin.username or admin.admin_user_id or "admin-user").strip() or "admin-user"
    perms = await get_admin_permissions(session, admin=admin)
    return (user_id, deployment_roles_from_permissions(perms))


async def _read_deployment_request_json(request: Request) -> dict[str, Any] | JSONResponse:
    """Parse JSON object from deployment POST bodies.

    Returns 400 ProblemDetails (no upstream proxy) when the body is not valid JSON
    or is not a JSON object.
    """
    try:
        body = await request.body()
        if not body:
            return {}
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return _problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid JSON body.",
            detail="Request body is not valid JSON.",
        )
    except UnicodeDecodeError:
        return _problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid JSON body.",
            detail="Request body is not valid UTF-8.",
        )
    if not isinstance(data, dict):
        return _problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid JSON body.",
            detail="Request body must be a JSON object.",
        )
    return data


@router.get("/plans")
async def list_plans(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path="/adaptation-plans",
        request=request,
    )


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adaptation-plans/{plan_id}",
        request=request,
    )


@router.get("/plans/{plan_id}/runs")
async def list_runs_for_plan(
    plan_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adaptation-plans/{plan_id}/runs",
        request=request,
    )


@router.post("/plans/{plan_id}/approve")
async def approve_plan(
    plan_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_APPROVE))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    approved_by, roles = await _deployment_identity(session, admin=admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adaptation-plans/{plan_id}/approve",
        request=request,
        json_body={"approvedByUserId": approved_by, "approverRoles": roles},
    )


@router.post("/plans/{plan_id}/run")
async def start_run(
    plan_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_OPERATE))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    created_by, _roles = await _deployment_identity(session, admin=admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adaptation-plans/{plan_id}/run",
        request=request,
        json_body={"createdByUserId": created_by},
        timeout_seconds=30.0,
    )


@router.get("/runs")
async def list_runs(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path="/adaptation-runs",
        request=request,
    )


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adaptation-runs/{run_id}",
        request=request,
    )


@router.get("/runs/{run_id}/manifest")
async def get_run_manifest(
    run_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adaptation-runs/{run_id}/manifest",
        request=request,
    )


@router.get("/runs/{run_id}/evaluation")
async def get_run_evaluation(
    run_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adaptation-runs/{run_id}/evaluation",
        request=request,
    )


@router.get("/runs/{run_id}/adapter-profile")
async def get_run_adapter_profile(
    run_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adaptation-runs/{run_id}/adapter-profile",
        request=request,
    )


@router.get("/profiles")
async def list_profiles(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path="/adapter-profiles",
        request=request,
    )


@router.get("/profiles/{profile_id}")
async def get_profile(
    profile_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adapter-profiles/{profile_id}",
        request=request,
    )


@router.get("/profiles/{profile_id}/activations")
async def list_profile_activations(
    profile_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adapter-profiles/{profile_id}/activations",
        request=request,
    )


@router.get("/profiles/{profile_id}/deployment-events")
async def list_profile_deployment_events(
    profile_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adapter-profiles/{profile_id}/deployment-events",
        request=request,
    )


@router.post("/profiles/{profile_id}/publish")
async def publish_profile(
    profile_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_PUBLISH))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    notes = raw.get("notes")
    notes_out: str | None
    if notes is None:
        notes_out = None
    elif isinstance(notes, str):
        notes_out = notes
    else:
        notes_out = str(notes)
    user_id, roles = await _deployment_identity(session, admin=admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adapter-profiles/{profile_id}/publish",
        request=request,
        json_body={
            "publishedByUserId": user_id,
            "roles": roles,
            "notes": notes_out,
        },
        upstream_headers=_idempotency_headers_from_request(request),
    )


@router.post("/profiles/{profile_id}/activate-canary")
async def activate_canary(
    profile_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_OPERATE))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    pct_raw = raw.get("canaryPercent") if "canaryPercent" in raw else raw.get("canary_percent")
    try:
        canary_percent = int(pct_raw) if pct_raw is not None else None
    except (TypeError, ValueError):
        canary_percent = None
    if canary_percent is None or canary_percent < 1 or canary_percent > 50:
        return _problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid canary percent.",
            detail="canaryPercent must be an integer between 1 and 50.",
        )
    user_id, roles = await _deployment_identity(session, admin=admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adapter-profiles/{profile_id}/activate-canary",
        request=request,
        json_body={
            "activatedByUserId": user_id,
            "roles": roles,
            "canaryPercent": canary_percent,
        },
        upstream_headers=_idempotency_headers_from_request(request),
    )


@router.post("/profiles/{profile_id}/promote")
async def promote_profile(
    profile_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_OPERATE))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    user_id, roles = await _deployment_identity(session, admin=admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adapter-profiles/{profile_id}/promote",
        request=request,
        json_body={"userId": user_id, "roles": roles},
        upstream_headers=_idempotency_headers_from_request(request),
    )


@router.post("/profiles/{profile_id}/rollback")
async def rollback_profile(
    profile_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_ROLLBACK))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    reason_raw = raw.get("reason")
    reason = (str(reason_raw).strip() if reason_raw is not None else "") or ""
    if not reason:
        return _problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid rollback reason.",
            detail="reason is required and cannot be empty or whitespace only.",
        )
    user_id, roles = await _deployment_identity(session, admin=admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adapter-profiles/{profile_id}/rollback",
        request=request,
        json_body={"userId": user_id, "roles": roles, "reason": reason},
        upstream_headers=_idempotency_headers_from_request(request),
    )


@router.get("/domains/{domain_key}/active-profile")
async def get_domain_active_profile(
    domain_key: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    encoded = quote(domain_key, safe="")
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/domains/{encoded}/active-profile",
        request=request,
    )


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_OPERATE))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    reason_raw = raw.get("reason")
    reason = (str(reason_raw).strip() if reason_raw is not None else "").strip()
    cancelled_by, _roles = await _deployment_identity(session, admin=admin)
    body: dict[str, Any] = {"cancelledByUserId": cancelled_by}
    if reason:
        body["reason"] = reason
    encoded = quote(run_id, safe="")
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adaptation-runs/{encoded}/cancel",
        request=request,
        json_body=body,
    )


@router.post("/runs/{run_id}/retry")
async def retry_run(
    run_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_OPERATE))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    created_by, _roles = await _deployment_identity(session, admin=admin)
    encoded = quote(run_id, safe="")
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adaptation-runs/{encoded}/retry",
        request=request,
        json_body={"createdByUserId": created_by},
        upstream_headers=_idempotency_headers_from_request(request),
    )


@router.post("/runs/{run_id}/resume")
async def resume_run(
    run_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_OPERATE))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    requested_by, _roles = await _deployment_identity(session, admin=admin)
    encoded = quote(run_id, safe="")
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adaptation-runs/{encoded}/resume",
        request=request,
        json_body={"requestedByUserId": requested_by},
        upstream_headers=_idempotency_headers_from_request(request),
    )


@router.get("/profiles/{profile_id}/drift-status")
async def get_profile_drift_status(
    profile_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    encoded = quote(profile_id, safe="")
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adapter-profiles/{encoded}/drift-status",
        request=request,
    )


@router.post("/profiles/{profile_id}/check-drift")
async def check_profile_drift(
    profile_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_OPERATE))],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    body: dict[str, Any] = {}
    if "kind" in raw:
        body["kind"] = raw.get("kind")
    encoded = quote(profile_id, safe="")
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adapter-profiles/{encoded}/check-drift",
        request=request,
        json_body=body,
    )


@router.get("/runs/queue/diagnostics")
async def get_queue_diagnostics(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path="/adaptation-runs/queue/diagnostics",
        request=request,
    )


def _trim_optional_reason(raw: dict[str, Any]) -> None:
    if "reason" not in raw:
        return
    value = raw.get("reason")
    trimmed = (str(value).strip() if value is not None else "").strip()
    if trimmed:
        raw["reason"] = trimmed
    else:
        raw.pop("reason", None)


def _strip_browser_identity_and_roles_fields(raw: dict[str, Any]) -> None:
    """Remove browser-supplied identity/role fields (case-insensitive, supports snake_case).

    The BO must never send authoritative user IDs / roles from the browser.
    """

    def norm(key: str) -> str:
        # requested_by_user_id -> requestedbyuserid, RequestedByUserId -> requestedbyuserid
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


@router.post("/runs/queue/repair/dry-run")
async def queue_repair_dry_run(
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_OPERATE))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    _strip_browser_identity_and_roles_fields(raw)
    _trim_optional_reason(raw)
    requested_by, _roles = await _deployment_identity(session, admin=admin)
    body = {"requestedByUserId": requested_by, **raw}
    return await proxy_adaptation_request(
        method="POST",
        upstream_path="/adaptation-runs/queue/repair/dry-run",
        request=request,
        json_body=body,
    )


@router.post("/runs/queue/repair")
async def queue_repair_apply(
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_OPERATE))],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> Response:
    raw = await _read_deployment_request_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    _strip_browser_identity_and_roles_fields(raw)
    _trim_optional_reason(raw)
    requested_by, _roles = await _deployment_identity(session, admin=admin)
    body = {"requestedByUserId": requested_by, **raw}
    return await proxy_adaptation_request(
        method="POST",
        upstream_path="/adaptation-runs/queue/repair",
        request=request,
        json_body=body,
    )

