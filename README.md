# Conexus

Conexus is a clean LLM gateway and monitoring back-office extracted from the useful LLM infrastructure already present in KGB.

The first target is simple:

```text
Admin login
→ configure provider
→ create project API key
→ call /v1/chat/completions
→ see request, provider, model, latency, tokens, cost, and errors in the BO
```

## Build strategy

This is not a theoretical rewrite. Start by harvesting the relevant LLM code from KGB, then simplify it into a standalone gateway.

Read first:

1. `docs/00_START_HERE.md`
2. `docs/01_KGB_REUSE_PLAN.md`
3. `docs/02_MILESTONES.md`
4. `docs/03_ARCHITECTURE.md`
5. `docs/04_GATEWAY.md`
6. `docs/05_BACK_OFFICE.md`
7. `docs/06_DEPLOYMENT.md`

## Main rule

Each milestone must run locally, deploy, and show its result in the BO or logs before the next milestone starts.
