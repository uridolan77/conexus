# Adapter profile runtime registry (Conexus Gateway)

Conexus Gateway maintains a **runtime registry** of adapter profiles that can be referenced by gateway requests and used for operational monitoring.

This registry is separate from the adaptation service lifecycle:

- **Adaptation lifecycle state**: “planned / evaluated / approved / published / promoted / rolled back” in `conexus.adaptation`.
- **Gateway runtime state**: “registered / canary / active” in Conexus Gateway.

## Concepts

- `adapterProfileId`: The profile identifier in `conexus.adaptation`.
- `gatewayProfileId`: The identifier Conexus Gateway issues and uses at runtime (prefix `gw-`).
- `domainKey`: The routing domain (e.g. `gaming-crm`).

## Request association (no behavior change by default)

`POST /v1/chat/completions` accepts optional headers:

- `X-Conexus-Domain-Key`: A domain key (e.g. `gaming-crm`).
- `X-Conexus-Gateway-Profile-Id`: A gateway profile id (e.g. `gw-...`).
  - For compatibility, Conexus also accepts `X-Conexus-Adapter-Profile-Id` as an alias for `X-Conexus-Gateway-Profile-Id` (same value: `gw-...`).

Current behavior:

- When an explicit `gatewayProfileId` is supplied and unknown, the gateway returns `400`.
- When `domainKey` is supplied and there is an active/canary state, Conexus attaches the selected profile id to the request log.
- When neither is supplied, Conexus preserves existing behavior.

By default, **canary traffic shifting is not enabled** (`ADAPTER_PROFILE_CANARY_ROUTING_ENABLED=false`). When enabled, Conexus can deterministically bucket requests by `(project_id, api_key_id, request_id)` for “active vs canary” selection (logging-first).

## Internal API key requirements (prod)

Internal endpoints under `/internal/*` are protected by `X-Internal-Api-Key` and are intended for trusted services only.

In **prod** with `ADAPTER_PROFILE_REGISTRY_ENABLED=true`, Conexus readiness (`GET /readyz`) will fail unless:

- `INTERNAL_ADAPTER_API_KEY` is set
- it is **not** `change-me`
- it is at least **32 characters**

## Activation history semantics

Conexus records activation transitions in `gateway_adapter_profile_activations` as append-only history.

- Creating canary writes/updates a row with `status="Canary"`.
- Promoting a profile creates a new row with `status="Active"`.
  - If the promoted profile previously had a canary row, that canary row is preserved and marked `status="Promoted"`.
  - If a different canary existed for the domain, it is preserved and marked `status="Retired"`.

When duplicate/corrupt activation rows exist, Conexus selects the newest row deterministically (by `created_at`) for active/canary resolution.

## Observability limitations

`GET /internal/adapter-profiles/{gatewayProfileId}/observability` currently computes only what Conexus can derive from `gateway_requests`:

- request count
- error rate
- latency p95
- cost per answer

Other metrics are returned as `null` until Conexus records those signals.

