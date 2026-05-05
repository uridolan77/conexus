# Conexus — Tech Debt Register

Last updated: 2026-05-04 (M5/M6 cleanup pass)

Severity:

- **P0**: correctness/security issue that can break production
- **P1**: serious reliability/maintainability problem
- **P2**: cleanup or structural improvement
- **P3**: polish/documentation

Status:

- **fixed**: resolved in this agent pass
- **deferred**: documented only

| ID | Area | File/function | Severity | Problem | Impact | Smallest safe fix | Status |
|---|---|---|---|---|---|---|---|
| TD-001 | Frontend lint | `.github/workflows/ci.yml`, `frontend/package.json` | P2 | CI runs frontend tests and build, but no lint step because ESLint is not installed/configured. | Style/accessibility regressions rely on tests/build only. | Add ESLint dev dependencies/config, then add `npm run lint` to CI. | deferred |
| TD-002 | Observability | `backend/app/core/logging.py` + gateway logs | P1 | No metrics/tracing; correlation is mostly via request_id header + DB rows. | Hard to diagnose latency/error spikes and provider incidents. | Add minimal structured logging fields and consider OTel later (defer). | deferred |
| TD-003 | Multi-replica correctness | `backend/app/services/gateway_service.py` (`_project_reserve_locks`) | P1 | Per-project `asyncio.Lock` is process-local; does not coordinate across workers/replicas. | Strictness depends on DB; assumptions may surprise operators. | Document clearly; consider Postgres-only row-lock reliance; consider distributed lock later. | **partial** — single-process warning comment added (2nd pass) |
| TD-004 | Admin brute-force limiting | `backend/app/services/admin_login_rate_limiter.py` | P1 | Rate limiter backend is in-memory only. | Not effective across multiple replicas. | Add redis-backed limiter later; document limitations. | deferred |
| TD-005 | Streaming accounting | `backend/app/services/gateway_service.py` streaming wrapper | P1 | Stream completion logging depends on finishing stream and receiving usage; interruptions yield partial token/cost fields. | BO usage/cost reporting may be skewed during stream failures. | Keep explicit tests for interruption, timeout, no-usage, and usage-event omission on incomplete usage. | **partial** - covered by tests; provider-specific post-stream usage fetching deferred |
| TD-006 | Provider config wiring | `backend/app/api/admin_providers.py` + `backend/app/llm/gateway_router.py` | P1 | BO-managed provider keys are stored/testable, but runtime provider selection uses env keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) only. | Operators may think BO provider config affects live gateway when it doesn’t. | Document in BO/UI and/or wiring plan; avoid changing behavior without owner decision. | deferred |
| TD-007 | Internal key management | `backend/app/api/internal_adapter_profiles.py` | P0 | `/internal/*` surface is guarded by a static header secret; exposure/misconfig is dangerous. | Control-plane compromise risk. | Ensure deployment guidance strongly restricts access; consider network-level ACL; consider rotation story. | **partial** — key never logged (confirmed); 503/404 guard tests added; startup prod check deferred (owner decision) |
| TD-008 | Observability endpoint scaling | `backend/app/api/internal_adapter_profiles.py:get_observability` | P1 | Computes stats by loading all matching rows into Python. | Can be expensive at scale. | Switch to aggregate SQL queries *only if output-identical*; add indexes if needed. | deferred |
| TD-009 | Doc drift | `docs/03_ARCHITECTURE.md` | P3 | Architecture docs can lag current schema and BO surfaces after rapid M5/M6 work. | Confuses onboarding and future refactors. | Keep architecture/checklist docs updated with each milestone. | **partial** - architecture and BO checklist refreshed in M6 cleanup |
| TD-010 | Request ID adoption | `backend/app/api/gateway.py` | P2 | No inbound request-id propagation. | Harder to correlate across upstream systems. | Optionally accept `X-Request-Id` as “parent” while preserving Conexus request id (defer). | deferred |

