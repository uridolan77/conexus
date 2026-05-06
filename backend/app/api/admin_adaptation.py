"""Admin proxy endpoints for the adaptation service.

This module intentionally exposes only a small, BO-shaped surface area.
The browser must never call the adaptation service directly.
"""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.admin_auth import get_admin_session
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
from app.services.admin_permissions_service import (
    ADAPTATION_APPROVE,
    ADAPTATION_OPERATE,
    ADAPTATION_PUBLISH,
    ADAPTATION_ROLLBACK,
    ADAPTATION_VIEW,
    require_adaptation_permission,
)
from app.services.adaptation_proxy_service import (
    deployment_identity as _deployment_identity,
    idempotency_headers_from_request as _idempotency_headers_from_request,
    proxy_adaptation_request,
    proxy_problem as _problem,
    read_deployment_request_json as _read_deployment_request_json,
    strip_browser_identity_and_roles_fields as _strip_browser_identity_and_roles_fields,
    trim_optional_reason as _trim_optional_reason,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/adaptation", tags=["admin"])


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

