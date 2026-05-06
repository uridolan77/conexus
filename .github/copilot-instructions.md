# GitHub Copilot Repository Instructions

Use `AGENTS.md` as the root instruction entrypoint.

For non-trivial work, immediately continue into the Conexus agent-os package:

1. `docs/spdd-agent-os-starter/.agent-os/profile.yml`
2. `docs/spdd-agent-os-starter/docs/product/conexus-v0-scope.md`
3. `docs/spdd-agent-os-starter/docs/architecture/architecture-principles.md`
4. `docs/spdd-agent-os-starter/docs/specs/provider-abstraction.md`
5. `docs/spdd-agent-os-starter/docs/specs/reasons-canvas.md`
6. `docs/spdd-agent-os-starter/docs/ai/SPDD_WORKFLOW.md`

Before coding:

- identify the smallest safe Conexus slice
- keep provider SDK details behind adapters
- preserve the current deployable milestone
- run the narrowest relevant validation or state why it could not run
