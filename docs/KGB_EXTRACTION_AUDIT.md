# KGB Extraction Audit

This audit lists what is taken from `uridolan77/KGB` for the Conexus v1 gateway
core, what is intentionally dropped, and where each surviving piece lands in
the new repo.

The goal of M1 is to get a small, gateway-shaped slice of the existing KGB
LLM layer running here without dragging in the KG pipeline assumptions.

## What we keep

| KGB source file | Pieces reused in Conexus | Change required | Conexus file |
|---|---|---|---|
| `backend/app/llm/base.py` | `BaseLLMRouter` ABC shape (interface contract: `call`, `aclose`, async ctx mgr) | Replace `stage_name` with `routing_profile`. Drop `stream_call` and `estimate_stage_cost` from the v1 surface. Drop `BudgetContext` parameter. | `backend/app/llm/base.py` |
| `backend/app/llm/router.py` | `LLMCallResult` dataclass; Anthropic `messages.create` call shape; tenacity retry wrapper around 429/5xx | Drop Redis caching, in-flight coalescing, semantic cache, shadow rollout, BudgetGuard, routing_store DB lookup, OTel shadow span. Keep just the call + retry + usage normalisation. | `backend/app/llm/anthropic_adapter.py` |
| `backend/app/llm/openai_router.py` | OpenAI `chat.completions.create` call shape; tenacity retry wrapper; usage mapping (`prompt_tokens`/`completion_tokens` → `input_tokens`/`output_tokens`) | Same drops as `router.py`. Keep call + retry + usage. | `backend/app/llm/openai_adapter.py` |
| `backend/app/llm/conexus_router.py` | Anthropic→OpenAI failover idea: try primary, on retryable error fall back to secondary; `ANTHROPIC_FAILOVER_ERRORS` / `OPENAI_FAILOVER_ERRORS` tuples; provider tagging on usage | Drop `CircuitBreakerRegistry`, `TokenTelemetry`, `BudgetContext`, `routing_store`, `agent_call`, `batch_submit`, model heuristics, complexity tier selection, prompt cache control blocks. Take only the linear "call primary, fall back to secondary on listed errors" behaviour. | `backend/app/llm/gateway_router.py` |
| `backend/app/llm/__init__.py` | `make_router()` provider factory pattern (`match settings.llm.provider`) | Use Conexus settings. Providers in v1: `openai`, `anthropic`, `gateway` (the failover router), `mock`. | `backend/app/llm/__init__.py` |
| `backend/app/llm/pricing.py` | `get_cost(model, input_tokens, output_tokens)` helper; YAML-backed pricing table with env override; lazy load with reload | Take as-is, point at the new `app/static_config/pricing.yaml`. Drop the `PRICING_OVERRIDES_JSON` env var only if it complicates v1 (kept for now — useful in tests). | `backend/app/llm/pricing.py` |
| `backend/app/static_config/pricing.yaml` | Per-model input/output prices for Anthropic + OpenAI | Copied verbatim. New models append here. | `backend/app/static_config/pricing.yaml` |
| `backend/app/llm/conexus_constants.py` | `ANTHROPIC_FAILOVER_ERRORS`, `OPENAI_FAILOVER_ERRORS` tuples | Inlined into `gateway_router.py` to keep the v1 module count low. | (inlined) |

## What we drop for v1

These KGB modules are out of scope for the Conexus first deployable slice and
are not copied at all:

```text
backend/app/llm/agent_runtime.py        # ReAct loop — out of scope
backend/app/llm/budget_guard.py         # belongs to a future budget module
backend/app/llm/circuit_breaker.py      # add later when we have multiple instances
backend/app/llm/conexus_format.py       # tool-calling format adapters
backend/app/llm/conexus_model_selection.py  # complexity heuristics
backend/app/llm/conexus_stream_setup.py # streaming retry helpers
backend/app/llm/conexus_types.py        # AgentResponse / TokenUsage TypedDict
backend/app/llm/exact_cache.py          # Redis prompt cache
backend/app/llm/heuristics.py           # PromptComplexityAnalyzer
backend/app/llm/mock.py                 # KG-specific mock router
backend/app/llm/prompt_cache_normalize.py
backend/app/llm/retry_logging.py        # ties into KGB structlog setup
backend/app/llm/routing_store.py        # DB-driven per-stage routing
backend/app/llm/semantic_cache_ops.py   # vector cache
backend/app/llm/semantic_router.py
backend/app/llm/telemetry.py            # KGB OTel + Redis budget telemetry
```

Conexus replaces these later with gateway-shaped equivalents (request log,
provider config in DB, OTel exporters, optional caching) once the basic
gateway is deployed.

## Concept translation

| KGB concept | Conexus replacement |
|---|---|
| `stage_name` (e.g. `"atom_extraction"`) | `routing_profile` / model alias (e.g. `"conexus-fast"`) |
| Static `_ROUTING_TABLE` mapping stage → `ModelConfig` | Project-level model alias resolved at request time (DB-backed in M3+; static map in M1) |
| `system: str` + `user: str` arguments | OpenAI-compatible `messages: list[ChatMessage]` |
| `BudgetContext` | Future `budgets` module — not in v1 |
| KGB pipeline telemetry (`LLM_TOKEN_USAGE` Prometheus metric) | `gateway_requests` row written by the gateway service |
| `LLMCallResult.cached` | Reserved for future cache module; always `False` in v1 |
| `ConexusRouter.call_messages` | Conexus `LLMProvider.chat()` |
| `ConexusRouter.agent_call` (tool-calling) | Out of v1 scope |

## v1 module shape

```text
backend/app/llm/
  __init__.py           # make_provider() factory
  base.py               # LLMProvider ABC: chat(messages, model, ...) -> ChatResult
  types.py              # ChatMessage, ChatResult, TokenUsage
  errors.py             # ProviderError, ProviderRateLimitError, ProviderUnavailableError, AllProvidersFailedError
  pricing.py            # get_cost() — copied
  openai_adapter.py     # OpenAIProvider (BaseLLMRouter-style call + tenacity retry)
  anthropic_adapter.py  # AnthropicProvider
  gateway_router.py     # GatewayProvider — Anthropic primary → OpenAI fallback
```

## Tests carried over (behavioural, not literal)

Behaviours we copy as test cases:

- OpenAI happy-path call returns content and token usage.
- Anthropic happy-path call returns content and token usage.
- Anthropic 429 / 5xx triggers gateway failover to OpenAI; result is tagged
  with `provider="openai"` and `fallback_used=True`.
- Pricing returns the right per-1M-token cost from the YAML.
- Pricing falls back to Sonnet rates for unknown models.

The actual KGB tests are not copied verbatim — they depend on `app.config`,
Redis, and the metrics module, none of which Conexus has in M1.
