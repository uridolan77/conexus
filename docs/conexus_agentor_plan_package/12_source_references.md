# 12 — Source References

This file records the repo evidence used for the plan.

## Repository metadata

- `uridolan77/conexus`: public, small repo, main branch, size ~807.
- `uridolan77/KGB`: private, main branch, size ~5509.
- `uridolan77/agentor`: public, main branch, size ~1305.
- `uridolan77/Aigent`: public, master branch, size ~323.
- `uridolan77/MCProToCall`: public, master branch, size ~834.
- `uridolan77/MCPServer`: public, master branch, size ~4776.
- `uridolan77/LLMGateway`: public, master branch, size ~262.
- `uridolan77/AutoResearch`: public, main branch, size ~26621.
- `uridolan77/ontogony-site`: public, main branch, size ~158578.
- `uridolan77/conexus.adaptation`: public, main branch, size ~823.
- `uridolan77/al.floys`: public, main branch, size ~11643.

## Conexus evidence

Inspected commit `49b97ac3d61946cafc5eb4f83e2e6b4926952f2c`, which added initial documentation/config for Conexus:

- `.env.example`
- `AGENTS.md`
- `docs/00_START_HERE.md`
- `docs/01_KGB_REUSE_PLAN.md`
- `docs/02_MILESTONES.md`
- `docs/03_ARCHITECTURE.md`
- `docs/04_GATEWAY.md`
- `docs/05_BACK_OFFICE.md`
- `docs/06_DEPLOYMENT.md`
- `docs/07_DATABASE_AND_AUTH.md`
- `docs/08_TESTING.md`
- `docs/09_FIRST_BUILD_PROMPT.md`
- `docs/adr/ADR-0001-stack-choice.md`

Key facts:

- Conexus is intended as an LLM gateway with BO.
- First checkpoint is `/v1/chat/completions → provider call → normalized response → DB request log → visible in BO`.
- KGB is explicitly identified as source repo for LLM code.
- FastAPI/Next.js/PostgreSQL is recommended for v1.

## KGB evidence

Inspected files:

- `backend/app/llm/base.py`
- `backend/app/llm/conexus_router.py`
- `backend/app/llm/openai_router.py`
- `backend/app/llm/router.py`
- `backend/app/llm/pricing.py`
- `backend/app/static_config/pricing.yaml`
- `backend/app/llm/__init__.py`
- `backend/app/llm/conexus_types.py`
- `backend/app/llm/conexus_format.py`
- `backend/app/llm/conexus_model_selection.py`
- `backend/app/llm/conexus_constants.py`
- `backend/app/api/errors.py`
- `backend/tests/unit/test_conexus_router_semantic.py`
- `docs/specs/CONEXUS.md`

Key facts:

- `BaseLLMRouter` defines async `call`, `stream_call`, `estimate_stage_cost`, `aclose`, and async context manager behavior.
- `ConexusRouter` implements Anthropic primary, OpenAI fallback, retryable failure handling, normalized usage, streaming, budget hooks, and `agent_call`.
- `OpenAIRouter` and `LLMRouter` provide provider-specific patterns.
- Pricing is centralized in YAML and Python loader.
- Typed contracts already exist for Conexus/Agentor: `TokenUsage`, `Message`, `ToolCall`, `AgentResponse`.
- Format conversion exists for OpenAI-format messages/tools to Anthropic.
- KGB tests contain useful behavior coverage for fallback, provider field in usage, streaming, cost estimation, and cleanup.

## MCProToCall evidence

Inspected commit `aa774187472ccc3ba714eed2c8b02a75c5a9508a`, which added project files. Evidence shows:

- Visual Studio solution with:
  - `ModelContextProtocol.Core`
  - `ModelContextProtocol.Server`
  - `ModelContextProtocol.Client`
  - `ModelContextProtocol.Extensions`
  - `BasicServer`
  - `BasicClient`
- README describes a secure C# MCP implementation.
- Claimed features include JSON-RPC 2.0, TLS, JWT auth, RBAC, input validation, rate limiting, structured logging.

Conclusion: good future .NET MCP/tool-layer asset.

## Aigent evidence

Inspected commit `e0bf7ff6fb21ae9f7148aeabf68077bdf3efda57`.

Observed concepts:

- memory backend config: Redis, SQL, DocumentDB/Mongo
- JWT/CORS/rate-limit config
- safety settings
- `IMessageBus` and in-memory bus
- agent types: reactive, deliberative, hybrid, learning, utility-based, BDI
- `IAgent`, `IAction`, `ActionResult`, `EnvironmentState`
- BDI concepts: beliefs, desires, intentions, plans

Conclusion: concept archive, not active implementation base.

## LLMGateway evidence

Inspected commit `a3f886ba97709cbc589ad57d225a66467acfed49`.

Observed concepts:

- Auth controller with login/register/refresh/logout.
- Admin users controller.
- Token usage analytics endpoint.
- JWT auth service registration.
- Token usage service.
- Router service registrations: content, cost, latency, smart model router.
- Background report/health-check schedules.

Conclusion: useful design reference for BO/admin/auth/analytics; not v1 code base.

## MCPServer evidence

Inspected commit `af962c625f17a4faa41b70e144287efc40cc5b59`.

Observed concepts:

- database schema extraction from SQL Server
- connection testing
- data transfer controllers
- mappings
- migration and validation endpoints

Conclusion: useful for future schema tool behavior; MCProToCall is the cleaner MCP foundation.

## AutoResearch evidence

Inspected commit `0b919f90eae145339a7111fed996f406df3fcb05`.

Observed concepts:

- FastAPI, Celery, Redis, SQLite/SQLAlchemy
- Git worktree-per-experiment lifecycle
- proposer/judge LLM split
- encrypted secret store
- evaluator/session/experiment/run models
- health endpoint

Conclusion: useful future pattern for Agentor evaluator/HITL/code-change workflows.

## Ontogony-site evidence

Inspected `package.json`.

Observed:

- Astro
- TinaCMS
- MDX
- React/Tailwind
- audit scripts: slugs, quizzes, flashcards
- check/build flow

Conclusion: best first real Agentor workflow target.

## Conexus.Adaptation evidence

Inspected `README.md`.

Observed:

- adaptation orchestrator for adapter profiles
- plan/run lifecycle
- recipe registry
- evaluation harness
- security threat model
- drift detection
- profile deployment/canary/rollback

Conclusion: strong v2/v3 roadmap, not v1.

## al.floys evidence

Inspected `package.json`.

Observed:

- Vite/React/TypeScript
- artificial-life playground description
- tests, benchmarks, ecosystem QA smoke scripts

Conclusion: separate product; avoid coupling to Conexus/Agentor.
