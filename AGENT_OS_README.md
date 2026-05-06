# Conexus Agent OS Package

This repository is governed by the **Conexus Agent OS package**, which is installed at the repository root.

## Canonical Source of Truth

The following files/folders are the **authoritative sources** for all agent-assisted work in Conexus:

### Core Instructions

- **`AGENTS.md`** — Agent operating rules, working agreements, and quick-start for the Conexus project
- **`CLAUDE.md`** — Claude Code-specific adapter
- **`GEMINI.md`** — Gemini CLI-specific adapter
- **`.github/copilot-instructions.md`** — GitHub Copilot-specific adapter
- **`CONVENTIONS.md`** — Project naming conventions and patterns

### Governance Layer

- **`.agent-os/profile.yml`** — Project identity, stack, validation commands, protected paths
- **`.agent-os/policy/command-policy.yml`** — Blocked and ask-before commands
- **`.agent-os/policy/protected-files.yml`** — Protected documentation and sensitive paths
- **`.agent-os/checklists/`** — Delivery-ready checklists
- **`.agent-os/snippets/`** — Reviewer prompts (gateway, BO, prompt-registry, etc.)
- **`.agent-os/templates/`** — Feature spec and PR summary templates
- **`.agent-os/manifest.json`** — Package metadata

### Product & Architecture

- **`docs/product/conexus-v0-scope.md`** — v0 feature scope, acceptance criteria, and non-goals
- **`docs/architecture/architecture-principles.md`** — Non-negotiable architectural constraints
- **`docs/specs/provider-abstraction.md`** — Provider adapter contract and normalization rules
- **`docs/specs/reasons-canvas.md`** — REASONS canvas template for feature work

### Process Guidance

- **`docs/ai/SPDD_WORKFLOW.md`** — Structured-Prompt-Driven Development workflow
- **`docs/ai/OPERATING_MODES.md`** — Agent operating modes (ASK, PLAN, IMPLEMENT, REVIEW, DEBUG, DOCUMENT, RESCUE)
- **`docs/ai/AGENT_OS_GUIDE.md`** — General AI system guidance
- **`docs/ai/REPO_ONBOARDING.md`** — Onboarding new team members
- **`docs/ai/HOOK_POLICY.md`** — Claude hooks safety and execution policy
- **`docs/ai/TOOL_SUPPORT_MATRIX.md`** — Feature matrix across tool adapters

### Tool Adapters

- **`.cursor/rules/`** — Cursor editor rules and workflows
- **`.windsurf/rules/`** — Windsurf editor rules
- **`.windsurf/workflows/`** — Windsurf workflow templates
- **`.continue/rules/`** — Continue extension rules
- **`.aider.conf.yml`** — Aider configuration
- **`.claude/settings.json`** — Claude configuration
- **`.claude/hooks/`** — Claude execution hooks

### Installation & Validation

- **`tools/validate-agent-os.py`** — Validates Agent OS package installation
- **`tools/install-agent-os.py`** — Installs Agent OS into other repositories
- **`tools/sync-adapters.py`** — Syncs tool adapters between repos

---

## What is NOT Canonical

### Starter Package

The folder **`docs/spdd-agent-os-starter/`** is a **reusable template/reference**, not the active source of truth for Conexus.

It contains the same files but is intended for other projects to bootstrap their own Agent OS packages. Do **not** read from the starter folder; always read from root paths.

### Runtime Documentation

The numbered docs under `docs/` (like `00_START_HERE.md`, `01_KGB_REUSE_PLAN.md`, etc.) are runtime delivery docs for Conexus v0, not part of the Agent OS governance layer. They are useful for understanding the project but not authoritative for agent behavior.

---

## Quick-Start for Agents

Before non-trivial implementation work in Conexus:

1. Read `AGENTS.md` (this repository)
2. Read `.agent-os/profile.yml` (project identity and validation)
3. Read `docs/product/conexus-v0-scope.md` (feature scope)
4. Read `docs/architecture/architecture-principles.md` (architectural constraints)
5. Read `docs/specs/provider-abstraction.md` (provider contract)
6. If implementing: read `docs/ai/SPDD_WORKFLOW.md` and use `docs/specs/reasons-canvas.md`

---

## Updating the Agent OS Package

The Agent OS package is version-controlled in the `agent-os` branch and merged regularly. When making changes to governance, instructions, or validation:

1. Make changes in root files (canonical)
2. Optionally sync back to `docs/spdd-agent-os-starter/` for future template use
3. Commit with message: `chore: update Agent OS governance <what changed>`
4. The starter package is kept in sync but marked as non-canonical

---

## Questions?

- **For Conexus product scope:** See `docs/product/conexus-v0-scope.md`
- **For agent working agreements:** See `AGENTS.md`
- **For architecture constraints:** See `docs/architecture/architecture-principles.md`
- **For development process:** See `docs/ai/SPDD_WORKFLOW.md`
