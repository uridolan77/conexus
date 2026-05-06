# REASONS Canvas: Extract OpenAI Provider Adapter (M1)

**Status:** Example implementation slice  
**Milestone:** M1 — Extract KGB gateway core  
**Project:** Conexus  
**Created:** 2026-05-06  
**Audience:** Backend developers, agent reviewers

---

## R — Requirements

What user-visible or operator-visible behavior must change?

The Conexus gateway must expose a **working OpenAI endpoint** (`POST /v1/chat/completions`) that accepts normalized requests and returns normalized responses. Operators must be able to call the gateway with an OpenAI-compatible client and receive real LLM responses.

This is the foundation for M2 (first real gateway call).

---

## E — Evidence / Current Behavior / Examples

What current code, docs, tests, or KGB behavior show the problem or target state?

**Current state:**
- KGB has working `OpenAIRouter` and `BaseLLMRouter` implementations in `backend/app/llm/openai_router.py` and `backend/app/llm/base.py`
- KGB tests demonstrate OpenAI request mapping, token counting, and cost calculation
- Conexus backend has skeleton gateway at `backend/app/api/gateway.py` (requires implementation)

**Target behavior (from docs):**
- See `docs/04_GATEWAY.md` — "M2-M5: OpenAI only" section
- See `docs/02_MILESTONES.md` — M1 acceptance criteria
- See `docs/product/conexus-v0-scope.md` — provider contract requirements

**Example KGB code to extract:**
```
backend/app/llm/base.py         (BaseLLMRouter interface)
backend/app/llm/openai_router.py (OpenAI implementation)
```

---

## A — Architecture / Boundaries

Which Conexus layers are affected? Does the change cross provider abstraction boundaries?

**Layers affected:**
1. **Provider abstraction layer** (new)
   - `backend/app/llm/providers/base.py` — Abstract provider interface
   - `backend/app/llm/providers/openai_adapter.py` — OpenAI implementation
   - `backend/app/llm/providers/fake_provider.py` — Fake provider for unit tests

2. **Router layer** (new)
   - `backend/app/llm/provider_factory.py` — Provider resolution by name/key

3. **Gateway API layer** (modify existing)
   - `backend/app/api/gateway.py` — Call provider adapter from the endpoint

**Boundaries:**
- Provider abstraction is **mandatory** (see `docs/architecture/architecture-principles.md`)
- Provider SDK types (OpenAI's `ChatCompletion`, `StreamingResponse`) must NOT leak outside adapters
- Normalized request/response types (from `docs/specs/provider-abstraction.md`) are the contract
- Do NOT couple to Agentor, backend workers, or database during this slice

**OK to use in gateway:**
- Database session (for request logging, added in M2)
- FastAPI request/response (for HTTP)
- Project API key validation (M2)

---

## S — Scope / Non-Goals

What is in scope for this slice? What is explicitly out of scope?

**In scope:**
- Extract `BaseLLMRouter` interface → normalized `ProviderAdapter` base class
- Implement OpenAI adapter with request normalization and response mapping
- Add fake provider for unit tests (allows M1 to validate without hitting OpenAI)
- Token counting via OpenAI's tokenizer
- Basic cost estimation (pricing.py extract)
- Unit tests for adapter lifecycle, request mapping, token counting, errors
- Update `backend/app/api/gateway.py` to use the new provider layer

**Not in scope (save for later milestones):**
- Database request logging (M2)
- Project API key authentication (M2)
- Multiple providers (M6 for Anthropic)
- Provider fallback (M6)
- Streaming responses (future)
- Tool/function calling (future)
- Error recovery beyond provider-level exceptions

**Out of scope decisions:**
- Do NOT implement `ConexusRouter` (failover/fallback) — that's M6
- Do NOT touch Agentor validation in this slice
- Do NOT add request caching or rate limiting

---

## O — Operations / Validation / Rollout

Which validation commands prove the change? Are there migration or rollout implications?

**Validation commands (run before landing):**

```bash
# Install and lint
python -m pip install -e ./backend[dev]
python -m ruff check backend
python -m mypy backend/app

# Unit tests (must pass before merge)
python -m pytest backend/tests/test_openai_adapter.py -v

# Integration test (optional, nice to have)
python -m pytest backend/tests/test_gateway_openai.py -v
```

**Manual validation:**

```bash
# Optional: test real OpenAI call locally (requires OPENAI_API_KEY)
python -m pytest backend/tests/test_openai_adapter.py::test_real_openai_call -v
```

**No deployment implications:**
- This is backend-only code changes
- No migrations needed (request logging comes in M2)
- No environment variable changes needed yet (keys added in M2)

---

## N — Norms / Naming / Contracts

Which API names, model identifiers, provider keys, or trace fields are affected?

**New type names:**
- `ProviderAdapter` — base class for all providers
- `ProviderRequest` — normalized request shape (see `docs/specs/provider-abstraction.md`)
- `ProviderResponse` — normalized response shape
- `ProviderError` — normalized error with codes

**Model identifier:**
- Use `"gpt-4o"` (default) in v0. Other models added per-provider in M3.

**No new database fields** — but prepare for M2's `provider`, `model`, `status`, `latency_ms`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost` fields.

**Code structure (package):**
```
backend/app/llm/
├── __init__.py
├── providers/
│   ├── __init__.py
│   ├── base.py          # ProviderAdapter base class
│   ├── openai_adapter.py
│   └── fake_provider.py
├── provider_factory.py
└── pricing.py           # Extract from KGB, v0-scoped only
```

---

## S — Safety / Security / Reversibility

Is the change safe, secure, and reversible?

**Safety:**
- ✅ New code only (no changes to existing runtime paths)
- ✅ Provider SDK types isolated in adapters
- ✅ Fake provider allows testing without real API calls
- ✅ No changes to authentication until M2

**Security:**
- ✅ Do NOT log OpenAI API keys in code or tests
- ✅ Use environment variables for test keys only (`.env.test`, not in repo)
- ✅ Normalized response never leaks provider-internal fields
- ✅ Error messages scrubbed of sensitive data

**Reversibility:**
- ✅ New files under `backend/app/llm/providers/` can be deleted if needed
- ✅ Gateway endpoint stays backward-compatible (changed only internally)
- ✅ No database changes, so no migrations to roll back
- ✅ Can revert to KGB code path if needed

**Testing strategy:**
- Unit tests use fake provider (no API keys needed)
- Optional integration tests use real OpenAI (requires OPENAI_API_KEY env var, skipped in CI)
- Fake provider must pass same test suite as real providers to ensure contract compliance

---

## Success Criteria (from docs/02_MILESTONES.md)

✅ `mocked OpenAI call works`  
✅ `fake provider call works`  
✅ `provider factory resolves by name`  
✅ `unit test suite passes`

---

## Risk Assessment

**Low risk:**
- New code, not modifying existing gateway until integration
- Comprehensive test coverage before merge
- Provider boundary is well-defined and enforced

**Known follow-ups (next slices):**
1. M2 — Integrate with database request logging
2. M2 — Add OpenAI API key configuration in BO
3. M3 — Add OpenAI-specific model selection
4. M6 — Add Anthropic adapter (uses same base interface)

---

## Links

- [Provider Abstraction Spec](docs/specs/provider-abstraction.md)
- [Milestones](docs/02_MILESTONES.md)
- [Gateway Doc](docs/04_GATEWAY.md)
- [KGB Source](https://github.com/uridolan77/KGB)
