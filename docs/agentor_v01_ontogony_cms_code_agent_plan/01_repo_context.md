# 01 — Repo Context

Repository:

```text
uridolan77/conexus
```

Branch:

```text
integration-init
```

The branch already contains an `agentor/` package with:

```text
agentor/README.md
agentor/app/models.py
agentor/app/executor.py
agentor/app/clients/conexus.py
agentor/app/clients/tool.py
agentor/app/workflows/ontogony_cms.py
agentor/tests/
```

Treat current Agentor code as a useful spike, not a mature runtime.

## Critical package-name warning

If Conexus backend uses `backend/app`, avoid expanding another generic package named `app`.

Recommended rename, if low-risk:

```text
agentor/app -> agentor/agentor_runtime
```

If not done now, add a TODO and avoid growing imports.

## Dependency direction

Correct:

```text
Agentor -> Conexus HTTP API
Agentor -> Tool/MCP clients
Conexus -> provider adapters
```

Wrong:

```text
Conexus -> Agentor
Conexus -> Ontogony workflow
Agentor -> direct OpenAI/Anthropic SDK calls
```
