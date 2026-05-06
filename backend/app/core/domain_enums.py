"""StrEnum definitions for persisted string fields (gateway, limits, repairs).

Values match existing database rows and API payloads; use these instead of
free-floating literals in core paths.
"""

from __future__ import annotations

from enum import StrEnum


class GatewayRequestStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class GatewayAdaptationMode(StrEnum):
    EXPLICIT = "explicit"
    DOMAIN_ONLY = "domain_only"
    ACTIVE = "active"
    CANARY = "canary"


class GatewayAdapterProfileStatus(StrEnum):
    REGISTERED = "Registered"


class GatewayAdapterProfileActivationStatus(StrEnum):
    ACTIVE = "Active"
    CANARY = "Canary"
    RETIRED = "Retired"
    PROMOTED = "Promoted"
    ROLLED_BACK = "RolledBack"


class ProjectLimitMode(StrEnum):
    DISABLED = "disabled"
    SOFT = "soft"
    HARD = "hard"


class LimitReservationRepairKind(StrEnum):
    NO_GATEWAY_REQUEST = "no_gateway_request"
    GATEWAY_REQUEST_FAILED = "gateway_request_failed"
    COMPLETED_WITHOUT_RECONCILE = "gateway_request_completed_without_reconcile"
    STARTED_NOT_COMPLETED = "gateway_request_started_but_not_completed"
    UNKNOWN = "unknown"
