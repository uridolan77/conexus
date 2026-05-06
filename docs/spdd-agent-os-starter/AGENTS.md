# AGENTS.md

Canonical instructions for AI coding agents working on Conexus.

Tool-specific files such as `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/*`, `.windsurf/rules/*`, and `.continue/rules/*` must stay thin adapters that point back here.

## Repository identity

Read `.agent-os/profile.yml` before implementation work.

Conexus is a small deployed product, not a speculative platform. The immediate priority is a clean vertical slice for the LLM gateway and back office:

```text
curl /v1/chat/completions
-> provider call
-> normalized response
-> request log in DB
-> request visible in BO
```

Prefer copying and simplifying proven gateway code from KGB over inventing a new framework. Keep each milestone deployable.

## Source-of-truth documents

Read these in order before non-trivial implementation work:

```text
docs/00_START_HERE.md
docs/01_KGB_REUSE_PLAN.md
docs/02_MILESTONES.md
docs/03_ARCHITECTURE.md
docs/04_GATEWAY.md
docs/05_BACK_OFFICE.md
docs/06_DEPLOYMENT.md
```

Use this package as the Conexus agent operating layer:

```text
docs/spdd-agent-os-starter/docs/product/conexus-v0-scope.md
docs/spdd-agent-os-starter/docs/architecture/architecture-principles.md
docs/spdd-agent-os-starter/docs/specs/provider-abstraction.md
docs/spdd-agent-os-starter/docs/specs/reasons-canvas.md
docs/spdd-agent-os-starter/docs/ai/SPDD_WORKFLOW.md
docs/spdd-agent-os-starter/docs/ai/OPERATING_MODES.md
docs/spdd-agent-os-starter/.agent-os/profile.yml
docs/spdd-agent-os-starter/.agent-os/policy/
```

## Working agreements

1. Build Conexus as a working gateway and BO product, not a generic agent platform.
2. Prefer small vertical slices over broad rewrites.
3. Extract and refactor useful KGB code before inventing new abstractions.
4. Do not leak provider SDK details past the provider adapter boundary.
5. Do not couple Conexus to Agentor or any future orchestration layer.
6. Do not change public contracts without updating docs and tests in the same slice.
7. Do not remove tests or bypass validation to make progress look green.
8. Do not touch secrets, credentials, tokens, private keys, or `.env` values.
9. Do not run destructive git or database commands unless explicitly asked.
10. Prefer clear, maintainable code and explicit seams over clever abstractions.

## Development flow

1. **Orient**: Read the relevant scope, architecture, and provider spec.
2. **Frame**: Name the smallest Conexus slice being changed.
3. **Plan**: List touched files and validation commands.
4. **Implement**: Make focused, cohesive edits.
5. **Validate**: Run the smallest relevant tests, lint, or build commands.
6. **Review**: Compare the result against the scope and provider boundary.
7. **Summarize**: State what changed, how it was validated, and what remains risky.

## REASONS Canvas

Use the REASONS canvas for non-trivial work:

```text
R - Requirements
E - Evidence / examples / current behavior
A - Architecture / boundaries / affected components
S - Scope / non-goals
O - Operations / validation / rollout
N - Naming / contracts / conventions
S - Safety / security / reversibility
```

## Coding defaults

- Python: type hints on public surfaces; explicit request and response models; deterministic tests.
- FastAPI: keep API and application layers thin; push provider specifics behind adapters.
- TypeScript and React: small BO components; explicit props; accessible and operationally useful UI.
- SQL and migrations: explicit schema changes; no casual destructive operations.
- Adapters and integrations: prefer explicit mapper modules over implicit provider leakage.

## Validation

Run the smallest relevant suite before declaring success:

```bash
python -m ruff check backend agentor
python -m mypy backend/app
python -m pytest backend/tests
python -m pytest agentor/tests
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
```

If validation cannot run, say exactly why and what remains to be executed.

## Security and git constraints

Protected paths include `.env`, `.env.*`, `*.pem`, `*.key`, production settings, and the governance docs under `docs/product`, `docs/architecture`, and `docs/specs`.

Allowed without asking: `git status`, `git diff`, `git log --oneline -n 20`.

Ask before: `git commit`, `git push`, `git reset`, `git rebase`, `git clean`, dependency installs, migrations, or data-destructive docker commands.

## Reporting format

```text
Changed:
- ...

Validated:
- ...

Risks:
- ...

Next:
- ...
```
