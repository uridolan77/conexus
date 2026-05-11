# ADR-0004: Trace and usage ownership

## Status

Proposed (target end-state). Partially implemented today.

## Decision (target)

Conexus owns trace and usage events for all LLM calls.

Callers may provide (future contract enrichment):

- `trace_id`
- `caller.system` / `caller.component` / `caller.operation` / `caller.user_id`
- `metadata`

Conexus adds:

- selected provider
- selected model
- route decision metadata (today: provider + `fallback_used` on chat responses; richer route preview is not a public endpoint yet)
- token usage
- cost estimate (where pricing data exists)
- latency
- provider status
- normalized error shape for gateway errors

## Current implementation (May 2026)

- **Correlation id:** Gateway responses include `X-Conexus-Request-Id` and JSON `id` of the form `chatcmpl-{request_id}`. This id ties to `gateway_requests` / BO visibility. It is **not** the same field as a future first-class `trace_id` in JSON bodies described in early work-package examples.
- **Usage ledger:** `usage_events` rows are written when complete usage exists (see `app/services/usage_service.py`). There is **no** `GET /v1/usage/{id}` for project API keys yet.
- **Traces:** There is **no** `GET /v1/traces/{id}` public API. Operational visibility is via the back office and internal adapter observability endpoints.

## Rationale

Agentor and Athanor need end-to-end accountability. Provider logs alone are insufficient. Application logs alone are insufficient. Conexus is the only service that sees routing intent, provider execution, normalized result, and cost.

## Acceptance (target)

Every successful or failed LLM call produces a durable record suitable for operator and downstream analytics use cases.

Today, gateway request logs plus conditional usage events meet much of this for chat; public retrieval APIs and a unified `trace_id` field remain gaps documented in `docs/readiness/CONEXUS_APP_INTEGRATION_READINESS.md`.
