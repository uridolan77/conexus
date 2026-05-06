# GitHub Copilot Repository Instructions

Use `AGENTS.md` as the root instruction entrypoint.

For non-trivial work, immediately continue into the Conexus agent-os package (installed at root):

1. `.agent-os/profile.yml`
2. `docs/product/conexus-v0-scope.md`
3. `docs/architecture/architecture-principles.md`
4. `docs/specs/provider-abstraction.md`
5. `docs/specs/reasons-canvas.md`
6. `docs/ai/SPDD_WORKFLOW.md`

Before coding:

- identify the smallest safe Conexus slice
- keep provider SDK details behind adapters
- preserve the current deployable milestone
- run the narrowest relevant validation or state why it could not run
