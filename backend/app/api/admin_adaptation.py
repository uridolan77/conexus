"""Admin proxy endpoints for the adaptation service.

This module intentionally exposes only a small, BO-shaped surface area.
The browser must never call the adaptation service directly.
"""

from __future__ import annotations

import json
from typing import Annotated, Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.admin_auth import get_admin_session
from app.core.config import settings
from app.services.admin_auth_service import AdminSession

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


async def proxy_adaptation_request(
    *,
    method: str,
    upstream_path: str,
    request: Request,
    json_body: dict[str, Any] | None = None,
    timeout_seconds: float = 10.0,
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

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(method, url, params=params, json=json_body)
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
        return _problem(
            status_code=status.HTTP_502_BAD_GATEWAY,
            title="Adaptation proxy error.",
            detail="Unexpected error while proxying to adaptation service.",
        )

    return _response_from_upstream(upstream)


# Temporary: all authenticated BO admins receive full adaptation deployment roles until
# Conexus maps read-only vs operator capabilities.
_DEPLOYMENT_ROLES = (
    "ComplianceReviewer",
    "AdaptationPublisher",
    "AdaptationOperator",
)


def _deployment_identity(admin: AdminSession) -> tuple[str, list[str]]:
    user_id = (admin.username or admin.admin_user_id or "admin-user").strip() or "admin-user"
    return (user_id, list(_DEPLOYMENT_ROLES))


async def _read_json_object(request: Request) -> dict[str, Any]:
    try:
        body = await request.body()
        if not body:
            return {}
        data = json.loads(body.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


@router.get("/plans")
async def list_plans(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
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
    request: Request,
) -> Response:
    approved_by, roles = _deployment_identity(admin)
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
    request: Request,
) -> Response:
    created_by, _roles = _deployment_identity(admin)
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
    request: Request,
) -> Response:
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/adapter-profiles/{profile_id}/activations",
        request=request,
    )


@router.post("/profiles/{profile_id}/publish")
async def publish_profile(
    profile_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    request: Request,
) -> Response:
    raw = await _read_json_object(request)
    notes = raw.get("notes")
    notes_out: str | None
    if notes is None:
        notes_out = None
    elif isinstance(notes, str):
        notes_out = notes
    else:
        notes_out = str(notes)
    user_id, roles = _deployment_identity(admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adapter-profiles/{profile_id}/publish",
        request=request,
        json_body={
            "publishedByUserId": user_id,
            "roles": roles,
            "notes": notes_out,
        },
    )


@router.post("/profiles/{profile_id}/activate-canary")
async def activate_canary(
    profile_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    request: Request,
) -> Response:
    raw = await _read_json_object(request)
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
    user_id, roles = _deployment_identity(admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adapter-profiles/{profile_id}/activate-canary",
        request=request,
        json_body={
            "activatedByUserId": user_id,
            "roles": roles,
            "canaryPercent": canary_percent,
        },
    )


@router.post("/profiles/{profile_id}/promote")
async def promote_profile(
    profile_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    request: Request,
) -> Response:
    user_id, roles = _deployment_identity(admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adapter-profiles/{profile_id}/promote",
        request=request,
        json_body={"userId": user_id, "roles": roles},
    )


@router.post("/profiles/{profile_id}/rollback")
async def rollback_profile(
    profile_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    request: Request,
) -> Response:
    raw = await _read_json_object(request)
    reason_raw = raw.get("reason")
    reason = (str(reason_raw).strip() if reason_raw is not None else "") or ""
    if not reason:
        return _problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid rollback reason.",
            detail="reason is required and cannot be empty or whitespace only.",
        )
    user_id, roles = _deployment_identity(admin)
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adapter-profiles/{profile_id}/rollback",
        request=request,
        json_body={"userId": user_id, "roles": roles, "reason": reason},
    )


@router.get("/domains/{domain_key}/active-profile")
async def get_domain_active_profile(
    domain_key: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    request: Request,
) -> Response:
    encoded = quote(domain_key, safe="")
    return await proxy_adaptation_request(
        method="GET",
        upstream_path=f"/domains/{encoded}/active-profile",
        request=request,
    )

