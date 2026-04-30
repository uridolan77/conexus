# Conexus — Refactor Plan (Safe + Deferred)

Last updated: 2026-04-30

This is a **production-safety-first** plan. Items are grouped by what is safe to do now vs what needs an owner decision.

## Safe now (low risk, behavior-preserving)

- **CI hardening**
  - Add frontend `npm test` to `.github/workflows/ci.yml` (already `vitest run` exists).
  - Optionally add `npm run lint` in CI if it’s stable.
- **Gateway code clarity**
  - Reduce duplication in `backend/app/services/gateway_service.py` between stream and non-stream paths by extracting tiny private helpers (no behavior changes).
  - Improve log messages for failure paths (keep response shapes identical).
- **Internal adapter observability**
  - Replace Python materialization with SQL aggregates only if output-identical.
  - Add query bounds/limits if endpoints are used with large windows.
- **Docs**
  - Fix `docs/03_ARCHITECTURE.md` drift (mark aspirational tables as “future” or remove them).

## Needs owner decision (small scope but contract/behavior-adjacent)

- **Wire BO provider configs into runtime routing**
  - Today runtime uses env keys. Connecting DB-stored provider configs changes the operational contract.
  - Decision needed on precedence rules:
    - env-only vs db-only vs env overrides db
    - multiple provider configs + selection rules
    - safe rollout plan and observability
- **Request ID propagation**
  - Consider accepting an inbound correlation header (e.g. `X-Request-Id`) while still minting `X-Conexus-Request-Id`.
  - Needs decision on logging format and privacy constraints.
- **Distributed rate limiting / locks**
  - Admin login rate limiting and/or strict-limits reserve serialization across replicas would require Redis or a DB-based approach.
  - Decide if Conexus will run multi-replica soon.

## Larger architectural candidates (explicitly out of scope for “safe cleanup”)

- Add OpenTelemetry tracing + metrics (`/metrics`) + standardized dashboards
- Provider circuit breaker / health + dynamic routing policy engine
- Full OpenAI compatibility (tools, n>1, response formats, logprobs)

## Suggested order of work

1. CI: frontend tests in CI
2. Gateway clarity + targeted unit tests around stream edge cases
3. Observability endpoint aggregation (if necessary)
4. Docs drift fixes
5. Owner decision items (provider config wiring, request-id propagation, distributed rate limits)

## Risk estimates

- **Low**: CI changes; internal refactors with tests; docs updates
- **Medium**: observability query refactor (ensure identical semantics)
- **Medium/High**: provider config wiring into runtime; distributed rate limiting/locks

