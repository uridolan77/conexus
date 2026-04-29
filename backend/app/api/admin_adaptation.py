"""Admin proxy endpoints for the adaptation service.

This module intentionally exposes only a small, BO-shaped surface area.
The browser must never call the adaptation service directly.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

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


def _temporary_identity() -> tuple[str, list[str]]:
    # v0.3d: hardcoded. TODO before production: derive from authenticated BO admin session.
    return ("admin-user", ["ComplianceReviewer"])


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
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    request: Request,
) -> Response:
    approved_by, roles = _temporary_identity()
    return await proxy_adaptation_request(
        method="POST",
        upstream_path=f"/adaptation-plans/{plan_id}/approve",
        request=request,
        json_body={"approvedByUserId": approved_by, "approverRoles": roles},
    )


@router.post("/plans/{plan_id}/run")
async def start_run(
    plan_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    request: Request,
) -> Response:
    created_by, _roles = _temporary_identity()
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

