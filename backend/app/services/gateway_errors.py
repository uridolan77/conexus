"""Gateway-facing errors (HTTP-mapped) for chat completion orchestration."""

from __future__ import annotations

from datetime import datetime

from app.core.errors import ConexusDomainError


class GatewayClientError(ConexusDomainError):
    """Caller-visible 4xx — bad model, bad input."""

    http_status = 400

    def __init__(self, message: str, *, code: str, request_id: str) -> None:
        super().__init__(message, request_id=request_id)
        self.code = code
        self.request_id = request_id


class GatewayUpstreamError(ConexusDomainError):
    """Caller-visible 502/503 — all providers failed."""

    http_status = 502

    def __init__(self, message: str, *, code: str, request_id: str) -> None:
        super().__init__(message, request_id=request_id)
        self.code = code
        self.request_id = request_id


class GatewayLimitError(ConexusDomainError):
    """Caller-visible 429 — project hard limit exceeded."""

    http_status = 429

    def __init__(
        self,
        message: str,
        *,
        code: str,
        request_id: str,
        limit_type: str,
        current_value: float,
        limit_value: float,
        window: str,
        reset_at: datetime | None,
    ) -> None:
        super().__init__(
            message,
            request_id=request_id,
            limit_type=limit_type,
            current_value=current_value,
            limit_value=limit_value,
            window=window,
            reset_at=reset_at,
        )
        self.code = code
        self.request_id = request_id
        self.limit_type = limit_type
        self.current_value = current_value
        self.limit_value = limit_value
        self.window = window
        self.reset_at = reset_at
