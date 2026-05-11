# Architecture documentation index

This folder links **architecture narrative** to the longer **specifications** that already live under `docs/specs/`.

| Topic | Canonical doc | Notes |
| --- | --- | --- |
| High-level principles | `architecture-principles.md` | Product and engineering guardrails |
| Provider boundary (long-form) | `../specs/provider-abstraction.md` | Non-negotiable adapter rules for v0 |
| Runtime boundary (who calls whom) | `runtime-boundary.md` | Agentor/Athanor vs Conexus vs providers |
| Routing today vs forward-looking | `routing-policy.md` | YAML aliases vs aspirational catalog schema |
| Observability and cost | `observability-and-cost.md` | What exists in Postgres/BO today |

OpenAPI: `contracts/openapi/conexus.v1.yaml`  
Readiness: `../readiness/CONEXUS_APP_INTEGRATION_READINESS.md`
