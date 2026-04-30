# Internal contract: `conexus.adaptation` → Conexus Gateway

This document describes the internal HTTP contract that `conexus.adaptation` (planner/evaluator/lifecycle controller) can use to register and operate adapter profiles in Conexus Gateway (runtime registry/activation/observability).

All endpoints below are **internal** and require:

- Header: `X-Internal-Api-Key: <INTERNAL_ADAPTER_API_KEY>`

## Register a runtime profile

`POST /internal/adapter-profiles/register`

Request body:

```json
{
  "adapterProfileId": "ap-...",
  "domainKey": "gaming-crm",
  "runId": "run-...",
  "planId": "plan-...",
  "compositeScore": 0.87,
  "evidenceHash": "…",
  "semanticContextHash": "…",
  "slodModelVersion": "…",
  "profileVersion": "…",
  "metadata": {}
}
```

Response body:

```json
{
  "gatewayProfileId": "gw-...",
  "status": "Registered"
}
```

Notes:

- Registration is **idempotent by `adapterProfileId`**. A duplicate registration returns the existing `gatewayProfileId`.

## Activate canary

`POST /internal/adapter-profiles/{gatewayProfileId}/activate-canary`

Request body:

```json
{ "canaryPercent": 10, "metadata": {} }
```

Response body:

```json
{
  "domainKey": "gaming-crm",
  "gatewayProfileId": "gw-...",
  "status": "Canary",
  "canaryPercent": 10
}
```

## Promote

`POST /internal/adapter-profiles/{gatewayProfileId}/promote`

Response body:

```json
{
  "domainKey": "gaming-crm",
  "gatewayProfileId": "gw-...",
  "status": "Active",
  "previousGatewayProfileId": "gw-prev-..."
}
```

## Rollback

`POST /internal/adapter-profiles/{gatewayProfileId}/rollback`

Rolls back the active profile for the domain to the previously-active gateway profile id (when known).

## Read active profile for a domain

`GET /internal/domains/{domainKey}/active-profile`

Response body:

```json
{
  "domainKey": "gaming-crm",
  "gatewayProfileId": "gw-...",
  "status": "Active"
}
```

## Observability snapshot

`GET /internal/adapter-profiles/{gatewayProfileId}/observability?since=<iso>&until=<iso>`

Response body:

```json
{
  "gatewayProfileId": "gw-...",
  "windowStart": "2026-01-01T00:00:00+00:00",
  "windowEnd": "2026-01-02T00:00:00+00:00",
  "requestCount": 123,
  "errorRate": 0.01,
  "latencyP95Ms": 1200,
  "costPerAnswer": 0.0021,
  "citationFailureRate": null,
  "refusalRate": null,
  "userNegativeFeedbackRate": null
}
```

