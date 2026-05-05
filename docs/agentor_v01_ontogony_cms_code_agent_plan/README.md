# Agentor v0.1 — Ontogony CMS Agent Code-Agent Plan

Use this package as the execution plan for a coding agent working in `uridolan77/conexus`, ideally on `integration-init` or a new branch from it.

Goal: build **Agentor v0.1: Ontogony CMS Agent** as a minimal vertical slice.

Core rule:
- Agentor orchestrates workflow state.
- Conexus performs all LLM inference through `/v1/chat/completions`.
- MCP/tools provide source access.
- Human approval is required before writing files or opening PRs.

Do not turn Agentor into a broad multi-agent framework.
