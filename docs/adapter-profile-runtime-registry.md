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

