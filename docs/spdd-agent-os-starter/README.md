# Conexus Agent OS Package (Template)

⚠️ **Note**: The canonical Conexus agent-os package is now installed at the **repository root** (`.agent-os/`, root instruction files, etc.). 

This folder (`docs/spdd-agent-os-starter/`) is now a **reusable template/reference copy only**. It is not the active source of truth.

For Conexus development, read from root paths:
- `AGENTS.md`
- `.agent-os/profile.yml`
- `docs/product/conexus-v0-scope.md`
- `docs/specs/provider-abstraction.md`
- etc.

This folder is useful as a starting template for other projects, but agents working in the Conexus repo should use the root installation.

Generated/verified: 2026-05-06

## What is inside

```text
AGENTS.md                         canonical Conexus agent instructions
CLAUDE.md                         Claude Code adapter
GEMINI.md                         Gemini CLI adapter
CONVENTIONS.md                    manual/Aider conventions
.github/copilot-instructions.md   GitHub Copilot adapter
.github/instructions/*.md         Copilot path-specific adapters
.cursor/rules/*.mdc               Cursor rules
.windsurf/rules/*.md              Windsurf rules
.windsurf/workflows/*.md          Windsurf workflows
.continue/rules/*.md              Continue rules
.aider.conf.yml                   Aider configuration
.claude/skills/*/SKILL.md         repeatable development workflows
.claude/agents/*.md               review and specialist agents
.claude/hooks/*.py                deterministic guardrails
.claude/settings.json             Claude hook wiring
.agent-os/*                       Conexus policy, profile, templates, examples
tools/*.py                        copy and validation helpers
docs/product/*.md                 product scope docs for Conexus
docs/architecture/*.md            architecture principles for Conexus
docs/specs/*.md                   provider and planning specs for Conexus
docs/ai/*.md                      operating guide for agent-assisted Conexus work
```

## How to use it in this repo

Read these first:

```text
AGENTS.md
.agent-os/profile.yml
docs/product/conexus-v0-scope.md
docs/specs/provider-abstraction.md
docs/architecture/architecture-principles.md
```

Pair them with the main repo delivery docs:

```text
../00_START_HERE.md
../01_KGB_REUSE_PLAN.md
../02_MILESTONES.md
../03_ARCHITECTURE.md
../04_GATEWAY.md
../05_BACK_OFFICE.md
../06_DEPLOYMENT.md
```

## Validation helpers

```bash
python tools/validate-agent-os.py --target .
```

The installer remains available if you want to copy this package into another Conexus-oriented repo:

```bash
python tools/install-agent-os.py --target /path/to/repo
```

## First prompt for an agent

```text
Read AGENTS.md and .agent-os/profile.yml. Summarize the Conexus operating rules, source-of-truth docs, likely validation commands, and safety constraints. Do not edit files yet.
```

## Core principle

Do not duplicate long rules across tools. `AGENTS.md` is the source of truth. Tool-specific files stay thin. Skills and workflows capture repeatable procedure. Hooks and validation scripts enforce guardrails.
