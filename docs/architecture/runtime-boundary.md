# Runtime boundary

## Overview

Conexus is an LLM gateway. It is not an agent framework and not a knowledge engine.

```text
+-----------------+       +------------------+       +--------------------+
| Agentor (.NET)  | ----> | Conexus.Client   | ----> | Conexus API        |
+-----------------+       +------------------+       | Python/FastAPI     |
                                                       +---------+----------+
+-----------------+       +------------------+                 |
| Athanor (.NET)  | ----> | Conexus.Client   |                 v
+-----------------+       +------------------+       +--------------------+
                                                       | LLM Providers       |
                                                       +--------------------+
```

Trusted adaptation services may also call **internal** Conexus routes (`/internal/...`) using `X-Internal-Api-Key`; those are not browser APIs.

## Why this boundary matters

The LLM boundary is where provider complexity, cost, policy, and observability converge. It should not be scattered across the application layer.

## Invariants (as implemented today)

1. No direct provider calls from Agentor/Athanor for normal operation.
2. Every completed gateway response carries **`X-Conexus-Request-Id`** (and a matching `id` prefix on non-streaming JSON responses). Treat this as the correlation key for logs and support, not as a portable “trace document” API yet.
3. Model aliases resolve inside Conexus using `backend/static_config/model_aliases.yaml` plus gateway router logic.
4. Provider errors on supported paths are mapped to HTTP status codes with structured `detail` for gateway domain errors (see OpenAPI `HttpErrorWrapper`).
5. Token usage on successful non-streaming chat responses is returned in OpenAI-style `usage` object fields (`prompt_tokens`, `completion_tokens`, `total_tokens`).
6. Streaming responses may omit usage unless the provider emits a usage chunk; this is an intentional operational edge case documented in gateway tests.

## Not yet invariant

- A first-class `trace_id` field inside JSON bodies for chat (work-package examples showed this; Conexus v0 does not).
- A public `GET /v1/usage/...` or `GET /v1/traces/...` API for callers.
