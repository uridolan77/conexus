# M2/M3 Sanity Review

Changed:
- Implemented BO-config-first runtime provider resolution with env fallback.
- Added `backend/app/services/gateway_runtime_config_service.py`.
- Updated `backend/app/llm/dependencies.py` to resolve request-scoped providers from BO first.
- Added resolver test coverage in `backend/tests/test_gateway_runtime_config_service.py`.
- Updated smoke checklist and gateway documentation alignment.

Validated:
- `python tools/validate-agent-os.py --target .` passed.
- `python tools/check-starter-refs.py` passed.
- `python -m pytest backend/tests/test_gateway_runtime_config_service.py backend/tests/test_gateway_endpoint.py` passed (`48 passed`).
- `python -m pytest backend/tests` passed (`366 passed`).
- Reviewed required architecture/spec/scope docs and smoke-test checklist:
  - `AGENTS.md`
  - `.agent-os/profile.yml`
  - `docs/product/conexus-v0-scope.md`
  - `docs/architecture/architecture-principles.md`
  - `docs/specs/provider-abstraction.md`
  - `docs/specs/reasons-canvas.md`
  - `docs/ai/SPDD_WORKFLOW.md`
  - `docs/ai/M2_M3_SANITY_REVIEW.md`
  - `docs/specs/gateway-runtime-contract.md`
  - `.agent-os/checklists/first-real-smoke-test.md`
  - `docs/04_GATEWAY.md`
  - `docs/05_BACK_OFFICE.md`
  - `docs/06_DEPLOYMENT.md`

Works:
- `/v1/chat/completions` endpoint exists and accepts minimal request (`model`, `messages`) for non-streaming flow.
- Endpoint requires project API key auth via `Authorization: Bearer <project_api_key>`.
- Unsupported OpenAI fields are rejected safely for current compatibility subset (`n != 1`, `tools`, `tool_choice`, `logprobs`, unsupported `response_format`).
- Successful responses include: chat id, model, provider, usage, `fallback_used`, and `X-Conexus-Request-Id` header.
- Gateway request lifecycle writes request row before provider call and updates row after completion/failure.
- Successful provider calls are logged as `status=completed` with latency and usage/cost when available.
- Failed provider calls are logged as `status=failed` with error code/message and request id continuity.
- BO provider config CRUD/test path exists; provider keys are encrypted at rest and only masked values are returned by BO APIs.
- Gateway runtime now consumes BO provider configs for real request execution (per-provider), with env key fallback when BO config is absent/unusable.
- BO request list/detail endpoints and pages exist and show enough routing/latency/token/cost/error metadata for operational debugging.
- Deployment docs and env docs are broadly executable (`docker-compose`, Alembic, health/readiness, admin bootstrap flow).

Partially works:
- Response/request-id consistency is good for gateway-domain errors and compatibility validation errors, but not universal for all early failures (for example, auth 401 and framework-level 422 do not provide gateway request log rows).
- Validation-failure logging behavior is mixed:
  - Compatibility validation done in gateway handler before execution is not persisted to `gateway_requests`.
  - Provider-selection/runtime validation errors inside execution path are logged as failed rows.
- Streaming path is implemented and preserved, but smoke focus is non-streaming; streaming fallback behavior differs from non-streaming alias behavior.

Missing / broken:
- No runtime blocker identified from automated validation.
- Manual first real deployed smoke execution is still required to fully close operational readiness.

Risky / confusing:
- Runtime selection path remains split across provider configs, env fallback, and alias routing; operator-facing source visibility is still limited.
- For now, BO does not explicitly label per-request credential source (bo_config vs env fallback) in request details.

Smallest missing piece before smoke test:
- Execute the first real deployed manual smoke run and capture result artifacts in the runbook.

Decision:
- Ready with caveats

Next recommended slice:
- Title:
  - Operator visibility: runtime credential source in BO request diagnostics
- Goal:
  - Show whether each request used BO provider config or env fallback, reducing ambiguity during incident/debug flows.
- Files likely touched:
  - `backend/app/services/gateway_runtime_config_service.py`
  - `backend/app/services/request_log_service.py`
  - `backend/app/api/admin_requests.py`
  - `frontend/app/requests/page.tsx`
  - `backend/tests/test_gateway_endpoint.py`
  - `backend/tests/test_admin_requests.py`
  - `docs/05_BACK_OFFICE.md`
- Acceptance criteria:
  - Request logs include credential source (`bo_config` or `env`).
  - BO request list/detail surfaces credential source clearly.
  - No secrets or raw keys are exposed.
  - Existing gateway response/stream/log behavior is unchanged otherwise.
- Validation:
  - `python -m pytest backend/tests`
  - Targeted tests for credential-source field visibility and safety.
  - Manual deployed smoke flow with runbook result capture.
