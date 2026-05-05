# 11 — Review Checklist

## Architecture
- [ ] Agentor calls Conexus through HTTP, not direct provider SDKs.
- [ ] Conexus does not import Agentor.
- [ ] Tool access is abstracted behind ToolClient.
- [ ] MCP remains a tool boundary, not LLM routing.

## Safety
- [ ] No write occurs before approval.
- [ ] Filesystem access is root-restricted.
- [ ] Path traversal is rejected.
- [ ] Approval checkpoint includes target path and preview.
- [ ] Generated status is `draft`.

## Correctness
- [ ] Planner produces usable plan.
- [ ] Source node preserves source paths.
- [ ] Writer uses source bundle.
- [ ] Critic has four scores plus overall.
- [ ] Formatter matches Ontogony Astro/Tina schema.
- [ ] Resume does not re-run previous nodes.

## Tests
- [ ] All existing Agentor tests pass.
- [ ] New resume tests added.
- [ ] Tool path safety tests added.
- [ ] CMS formatter tests added.
- [ ] JSON parsing fallback tests added.

Reject the output if it adds DB, vector memory, A2A, direct OpenAI/Anthropic SDK calls inside Agentor, or autonomous write/PR before approval.
