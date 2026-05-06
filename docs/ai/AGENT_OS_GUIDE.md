# Agent OS Guide

This package is the Conexus operating layer for agent-assisted work. Its job is to keep tool adapters thin and keep implementation work anchored to Conexus scope, architecture, and provider-boundary docs.

## Layers

```text
Canonical instructions: AGENTS.md
Tool adapters: CLAUDE.md, GEMINI.md, Copilot, Cursor, Windsurf, Continue
Procedures: skills/workflows/snippets
Specialists: subagents/reviewer prompts
Enforcement: hooks, CI, tests
Source of truth: product/spec/architecture docs
```

## What belongs where

- `AGENTS.md`: stable Conexus operating rules.
- adapters: short tool-specific routing files.
- skills/workflows: repeatable Conexus procedures.
- subagents: noisy exploration and specialist review.
- hooks: deterministic enforcement.

## Conexus default reading order

1. `AGENTS.md`
2. `.agent-os/profile.yml`
3. `docs/product/conexus-v0-scope.md`
4. `docs/architecture/architecture-principles.md`
5. `docs/specs/provider-abstraction.md`
