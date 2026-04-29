"""Admin request monitoring endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import GatewayRequest, Project, ProjectApiKey
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession

router = APIRouter(prefix="/admin/requests", tags=["admin"])

SortBy = Literal["created_at", "completed_at", "latency_ms", "total_tokens", "estimated_cost"]
SortDir = Literal["asc", "desc"]
StatusGroup = Literal["success", "failure", "in_progress"]

SORT_COLUMNS = {
    "created_at": GatewayRequest.created_at,
    "completed_at": GatewayRequest.completed_at,
    "latency_ms": GatewayRequest.latency_ms,
    "total_tokens": GatewayRequest.total_tokens,
    "estimated_cost": GatewayRequest.estimated_cost,
}
SORT_DIRS = {"asc", "desc"}


class TokenSummary(BaseModel):
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


class CostSummary(BaseModel):
    estimated_cost: float | None
    currency: str = "USD"


class ErrorSummary(BaseModel):
    code: str | None
    message: str | None


class RoutingSummary(BaseModel):
    requested_model: str
    served_provider: str | None
    served_model: str | None
    fallback_used: bool


class RequestListItem(BaseModel):
    id: str
    request_id: str
    project_id: str | None
    project_name: str | None
    api_key_id: str | None
    api_key_prefix: str | None
    requested_model: str
    provider: str | None
    model: str | None
    status: str
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    estimated_cost: float | None
    fallback_used: bool
    error_code: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    duration_bucket: Literal["fast", "normal", "slow"] | None
    cost_bucket: Literal["free_or_unknown", "low", "medium", "high"]


class RequestListResponse(BaseModel):
    items: list[RequestListItem]
    limit: int
    offset: int
    total: int


class RequestDetail(RequestListItem):
    previous_request_id: str | None
    next_request_id: str | None
    request_age_seconds: int | None
    completed_age_seconds: int | None
    normalized_status_group: StatusGroup
    token_summary: TokenSummary
    cost_summary: CostSummary
    error_summary: ErrorSummary
    routing_summary: RoutingSummary


def _duration_bucket(latency_ms: int | None) -> Literal["fast", "normal", "slow"] | None:
    if latency_ms is None:
        return None
    if latency_ms < 1_000:
        return "fast"
    if latency_ms < 5_000:
        return "normal"
    return "slow"


def _cost_bucket(cost: float | None) -> Literal["free_or_unknown", "low", "medium", "high"]:
    if cost is None or cost <= 0:
        return "free_or_unknown"
    if cost < 0.01:
        return "low"
    if cost < 0.10:
        return "medium"
    return "high"


def _status_group(status_value: str) -> StatusGroup:
    if status_value == "completed":
        return "success"
    if status_value == "failed":
        return "failure"
    return "in_progress"


def _age_seconds(value: datetime | None) -> int | None:
    if value is None:
        return None
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0, int((now - value).total_seconds()))


def _to_list_item(
    row: GatewayRequest,
    project_name: str | None,
    api_key_prefix: str | None,
) -> RequestListItem:
    return RequestListItem(
        id=row.id,
        request_id=row.request_id,
        project_id=row.project_id,
        project_name=project_name,
        api_key_id=row.api_key_id,
        api_key_prefix=api_key_prefix,
        requested_model=row.requested_model,
        provider=row.provider,
        model=row.model,
        status=row.status,
        latency_ms=row.latency_ms,
        prompt_tokens=row.prompt_tokens,
        completion_tokens=row.completion_tokens,
        total_tokens=row.total_tokens,
        estimated_cost=row.estimated_cost,
        fallback_used=row.fallback_used,
        error_code=row.error_code,
        error_message=row.error_message,
        created_at=row.created_at,
        completed_at=row.completed_at,
        duration_bucket=_duration_bucket(row.latency_ms),
        cost_bucket=_cost_bucket(row.estimated_cost),
    )


def _with_safe_joins(stmt: Select) -> Select:
    return stmt.outerjoin(Project, GatewayRequest.project_id == Project.id).outerjoin(
        ProjectApiKey,
        GatewayRequest.api_key_id == ProjectApiKey.id,
    )


def _apply_filters(
    stmt: Select,
    *,
    request_id: str | None,
    project_id: str | None,
    api_key_id: str | None,
    status_value: str | None,
    provider: str | None,
    model: str | None,
    requested_model: str | None,
    fallback_used: bool | None,
    error_code: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
    completed_from: datetime | None,
    completed_to: datetime | None,
    min_latency_ms: int | None,
    max_latency_ms: int | None,
    min_total_tokens: int | None,
    max_total_tokens: int | None,
    min_estimated_cost: float | None,
    max_estimated_cost: float | None,
) -> Select:
    if request_id:
        stmt = stmt.where(GatewayRequest.request_id == request_id)
    if project_id:
        stmt = stmt.where(GatewayRequest.project_id == project_id)
    if api_key_id:
        stmt = stmt.where(GatewayRequest.api_key_id == api_key_id)
    if status_value:
        stmt = stmt.where(GatewayRequest.status == status_value)
    if provider:
        stmt = stmt.where(GatewayRequest.provider == provider)
    if model:
        stmt = stmt.where(GatewayRequest.model == model)
    if requested_model:
        stmt = stmt.where(GatewayRequest.requested_model == requested_model)
    if fallback_used is not None:
        stmt = stmt.where(GatewayRequest.fallback_used == fallback_used)
    if error_code:
        stmt = stmt.where(GatewayRequest.error_code == error_code)
    if created_from:
        stmt = stmt.where(GatewayRequest.created_at >= created_from)
    if created_to:
        stmt = stmt.where(GatewayRequest.created_at <= created_to)
    if completed_from:
        stmt = stmt.where(GatewayRequest.completed_at >= completed_from)
    if completed_to:
        stmt = stmt.where(GatewayRequest.completed_at <= completed_to)
    if min_latency_ms is not None:
        stmt = stmt.where(GatewayRequest.latency_ms >= min_latency_ms)
    if max_latency_ms is not None:
        stmt = stmt.where(GatewayRequest.latency_ms <= max_latency_ms)
    if min_total_tokens is not None:
        stmt = stmt.where(GatewayRequest.total_tokens >= min_total_tokens)
    if max_total_tokens is not None:
        stmt = stmt.where(GatewayRequest.total_tokens <= max_total_tokens)
    if min_estimated_cost is not None:
        stmt = stmt.where(GatewayRequest.estimated_cost >= min_estimated_cost)
    if max_estimated_cost is not None:
        stmt = stmt.where(GatewayRequest.estimated_cost <= max_estimated_cost)
    return stmt


@router.get("", response_model=RequestListResponse)
async def list_requests(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    request_id: str | None = None,
    project_id: str | None = None,
    api_key_id: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    requested_model: str | None = None,
    model_search: str | None = None,
    fallback_used: bool | None = None,
    error_code: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    completed_from: datetime | None = None,
    completed_to: datetime | None = None,
    min_latency_ms: int | None = None,
    max_latency_ms: int | None = None,
    min_total_tokens: int | None = None,
    max_total_tokens: int | None = None,
    min_estimated_cost: float | None = None,
    max_estimated_cost: float | None = None,
    sort_by: SortBy = "created_at",
    sort_dir: SortDir = "desc",
) -> RequestListResponse:
    if sort_by not in SORT_COLUMNS or sort_dir not in SORT_DIRS:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="invalid sort")

    list_stmt = select(
        GatewayRequest,
        Project.name.label("project_name"),
        ProjectApiKey.prefix.label("api_key_prefix"),
    )
    list_stmt = _with_safe_joins(list_stmt)
    count_stmt = select(func.count()).select_from(GatewayRequest)

    list_stmt = _apply_filters(
        list_stmt,
        request_id=request_id,
        project_id=project_id,
        api_key_id=api_key_id,
        status_value=status,
        provider=provider,
        model=model,
        requested_model=requested_model,
        fallback_used=fallback_used,
        error_code=error_code,
        created_from=created_from,
        created_to=created_to,
        completed_from=completed_from,
        completed_to=completed_to,
        min_latency_ms=min_latency_ms,
        max_latency_ms=max_latency_ms,
        min_total_tokens=min_total_tokens,
        max_total_tokens=max_total_tokens,
        min_estimated_cost=min_estimated_cost,
        max_estimated_cost=max_estimated_cost,
    )
    count_stmt = _apply_filters(
        count_stmt,
        request_id=request_id,
        project_id=project_id,
        api_key_id=api_key_id,
        status_value=status,
        provider=provider,
        model=model,
        requested_model=requested_model,
        fallback_used=fallback_used,
        error_code=error_code,
        created_from=created_from,
        created_to=created_to,
        completed_from=completed_from,
        completed_to=completed_to,
        min_latency_ms=min_latency_ms,
        max_latency_ms=max_latency_ms,
        min_total_tokens=min_total_tokens,
        max_total_tokens=max_total_tokens,
        min_estimated_cost=min_estimated_cost,
        max_estimated_cost=max_estimated_cost,
    )

    if model_search:
        pattern = f"%{model_search}%"
        model_condition = or_(
            GatewayRequest.requested_model.ilike(pattern),
            GatewayRequest.model.ilike(pattern),
        )
        list_stmt = list_stmt.where(model_condition)
        count_stmt = count_stmt.where(model_condition)

    sort_column = SORT_COLUMNS[sort_by]
    sort_expression = sort_column.asc() if sort_dir == "asc" else sort_column.desc()
    list_stmt = list_stmt.order_by(sort_expression, GatewayRequest.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(list_stmt)
    rows = result.all()
    total = int((await session.execute(count_stmt)).scalar_one())
    return RequestListResponse(
        items=[
            _to_list_item(
                row,
                project_name=project_name,
                api_key_prefix=api_key_prefix,
            )
            for row, project_name, api_key_prefix in rows
        ],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get("/{request_id}", response_model=RequestDetail)
async def get_request(
    request_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RequestDetail:
    stmt = (
        select(
            GatewayRequest,
            Project.name.label("project_name"),
            ProjectApiKey.prefix.label("api_key_prefix"),
        )
        .outerjoin(Project, GatewayRequest.project_id == Project.id)
        .outerjoin(ProjectApiKey, GatewayRequest.api_key_id == ProjectApiKey.id)
        .where(GatewayRequest.request_id == request_id)
    )
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="request not found")

    request_row, project_name, api_key_prefix = row
    base = _to_list_item(request_row, project_name=project_name, api_key_prefix=api_key_prefix)

    previous_request_id = (
        await session.execute(
            select(GatewayRequest.request_id)
            .where(
                GatewayRequest.created_at < request_row.created_at,
                GatewayRequest.request_id != request_row.request_id,
            )
            .order_by(GatewayRequest.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    next_request_id = (
        await session.execute(
            select(GatewayRequest.request_id)
            .where(
                GatewayRequest.created_at > request_row.created_at,
                GatewayRequest.request_id != request_row.request_id,
            )
            .order_by(GatewayRequest.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return RequestDetail(
        **base.model_dump(),
        previous_request_id=previous_request_id,
        next_request_id=next_request_id,
        request_age_seconds=_age_seconds(request_row.created_at),
        completed_age_seconds=_age_seconds(request_row.completed_at),
        normalized_status_group=_status_group(request_row.status),
        token_summary=TokenSummary(
            prompt_tokens=request_row.prompt_tokens,
            completion_tokens=request_row.completion_tokens,
            total_tokens=request_row.total_tokens,
        ),
        cost_summary=CostSummary(estimated_cost=request_row.estimated_cost),
        error_summary=ErrorSummary(code=request_row.error_code, message=request_row.error_message),
        routing_summary=RoutingSummary(
            requested_model=request_row.requested_model,
            served_provider=request_row.provider,
            served_model=request_row.model,
            fallback_used=request_row.fallback_used,
        ),
    )
