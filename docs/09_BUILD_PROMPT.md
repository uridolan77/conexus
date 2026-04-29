# 09 — First Build Prompt

Use this prompt when starting implementation in the blank repo:

```text
We are building Conexus, a standalone LLM gateway and BO, using KGB as the source for existing LLM router code.

Start with Milestone 0 and Milestone 1 only.

Tasks:
1. Create FastAPI backend skeleton with /health and /health/ready.
2. Create Next.js BO shell with Dashboard, Providers, Projects, Requests navigation.
3. Add docker-compose with PostgreSQL.
4. Extract/refactor these KGB files into backend/app/llm:
   - backend/app/llm/base.py
   - backend/app/llm/conexus_router.py
   - backend/app/llm/openai_router.py
   - backend/app/llm/router.py
   - backend/app/llm/pricing.py
5. Remove KG-specific assumptions: stage extraction, corpus, chunks, ontology, DAG, Celery.
6. Keep only provider interface, OpenAI adapter, Anthropic adapter, pricing, fallback behavior, and normalized token usage.
7. Add unit tests for OpenAI success, Anthropic success, fallback, and pricing.
8. Do not build advanced BO screens yet. Only shell and health status.

Acceptance:
- backend runs
- frontend runs
- postgres runs
- /health returns OK
- LLM adapter tests pass
- code is ready for M2 gateway endpoint
```
