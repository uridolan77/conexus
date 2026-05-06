# Agent Instructions

Build Conexus as a small deployed product, not a large speculative platform.

## Canonical package

Use the Conexus agent-os package under `docs/spdd-agent-os-starter/` as the operating layer for agent-assisted work.

Read these first before non-trivial implementation work:

```text
AGENTS.md
docs/spdd-agent-os-starter/.agent-os/profile.yml
docs/spdd-agent-os-starter/docs/product/conexus-v0-scope.md
docs/spdd-agent-os-starter/docs/architecture/architecture-principles.md
docs/spdd-agent-os-starter/docs/specs/provider-abstraction.md
docs/spdd-agent-os-starter/docs/specs/reasons-canvas.md
docs/spdd-agent-os-starter/docs/ai/SPDD_WORKFLOW.md
docs/spdd-agent-os-starter/docs/ai/OPERATING_MODES.md
```

Treat the package docs as the source of truth for:

- Conexus scope boundaries
- provider abstraction rules
- REASONS/SPDD workflow
- agent operating modes
- protected docs and guardrails

## Current priority

Create a standalone Conexus repo by extracting the useful LLM gateway code from KGB.

## Working style

- Prefer small vertical slices.
- Copy/refactor useful KGB code before inventing new code.
- Keep each milestone deployable.
- Keep docs short and current.
- Make the BO useful early.
- Keep provider SDK details behind Conexus adapters.

## First successful checkpoint

A real request should flow through Conexus:

```text
curl /v1/chat/completions
→ provider call
→ normalized response
→ request log in DB
→ request visible in BO
```

## KGB source repo

Use:

```text
uridolan77/KGB
```

Primary source paths:

```text
backend/app/llm/base.py
backend/app/llm/conexus_router.py
backend/app/llm/openai_router.py
backend/app/llm/router.py
backend/app/llm/pricing.py
backend/app/llm/__init__.py
docs/specs/CONEXUS.md
```

Refactor them into standalone Conexus modules. Do not keep KG pipeline assumptions in the new repo.
