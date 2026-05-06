# Claude Code Instructions

Read `AGENTS.md` first. It is the canonical instruction file for this repository.

Use Claude-specific capabilities this way:

- `CLAUDE.md`: stable project context only.
- `.claude/skills/*`: repeatable workflows.
- `.claude/agents/*`: specialist review and isolated exploration.
- `.claude/hooks/*`: deterministic safety checks.
- `.claude/settings.json`: hook wiring.

Before implementation work, check `.agent-os/profile.yml` and relevant docs under `docs/product`, `docs/architecture`, and `docs/specs`.
