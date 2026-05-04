# Conexus + Agentor + MCP Integration Plan Package

Prepared for the `uridolan77` repo ecosystem after inspecting the accessible GitHub repositories and the key source/docs/commit evidence around:

- `uridolan77/conexus`
- `uridolan77/KGB`
- `uridolan77/agentor`
- `uridolan77/Aigent`
- `uridolan77/MCProToCall`
- `uridolan77/MCPServer`
- `uridolan77/LLMGateway`
- `uridolan77/AutoResearch`
- `uridolan77/ontogony-site`
- `uridolan77/conexus.adaptation`
- `uridolan77/al.floys`

## Executive decision

Build **Conexus first** as the deployed LLM gateway and BO. Use **KGB** as the primary source for reusable LLM provider/failover/pricing logic. Treat **Agentor/Aigent** as concept archives until Conexus has a working `/v1/chat/completions` path. Treat **MCProToCall** as the future MCP/tool-layer foundation, not part of Conexus core.

Recommended sequence:

```text
KGB LLM layer → Conexus gateway → minimal Agentor orchestration → MCP tools → Ontogony CMS workflow
```

## Package contents

| File | Purpose |
|---|---|
| `00_repo_research_report.md` | Evidence-based repo review and role assignment |
| `01_architecture_decision_record.md` | Formal decisions and anti-decisions |
| `02_conexus_kgb_extraction_plan.md` | Detailed KGB → Conexus extraction map |
| `03_target_architecture.md` | System boundaries and runtime architecture |
| `04_milestones_backlog.md` | Build order from M0 to Agentor/Ontogony slice |
| `05_cursor_prompts.md` | Cursor-ready prompts for implementation phases |
| `06_api_contracts.md` | Gateway API, BO API, and internal contracts |
| `07_database_schema.md` | Proposed Conexus relational schema |
| `08_testing_strategy.md` | Unit/integration/smoke test plan |
| `09_security_observability.md` | Auth, secrets, logging, cost, tracing and safety plan |
| `10_agentor_mcp_integration.md` | How Agentor, MCP, Aigent, MCProToCall fit later |
| `11_risks_and_cutline.md` | What to postpone and what to avoid importing |
| `12_source_references.md` | Source evidence log |
| `extraction_manifest.json` | Machine-readable extraction backlog |

## Core principle

Do not build another generalized framework yet. The first useful product slice is:

```text
A client can call Conexus with an OpenAI-compatible request,
Conexus chooses a provider,
records usage/cost/error,
and the BO shows the request.
```

Then build one Agentor workflow against a real product target: **Ontogony CMS page generation/review**.
