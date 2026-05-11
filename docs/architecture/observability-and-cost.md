# Observability and cost

## What Conexus records today

For gateway traffic, Conexus persists **gateway request rows** (latency, model, provider, status, estimated cost where available, error payloads, and correlation ids). Operators inspect these through the **back office** (authenticated admin session), not via unauthenticated public analytics APIs.

When token usage is complete, the system may also write **usage ledger** rows (`usage_events`) for downstream accounting. Admin endpoints under `/admin/usage/...` expose aggregates for operators.

## Internal adapter observability

When enabled, `GET /internal/adapter-profiles/{gatewayProfileId}/observability` returns windowed aggregates derived from stored gateway requests for a specific gateway profile id. This supports conexus.adaptation style workflows; it is **not** the same as a public `GET /v1/traces/{trace_id}` API.

## Forward-looking public usage/trace APIs

JSON Schemas under `contracts/json-schema/` with `x-contract-status: not-implemented` describe possible future public envelopes (`usage-event`, `trace-event`). They are intentionally **not** wired to live HTTP routes in v0.

## Cost estimation

Estimated cost depends on pricing tables and provider-reported usage. Clients should treat cost fields as **estimates** suitable for budgeting and trend analysis, not billing-grade invoices without reconciliation.
