# 00 — Mission Brief

## Product goal

Build `Agentor v0.1: Ontogony CMS Agent`.

Input:

```text
topic or page brief
optional source paths / source hints
optional target collection: essay | concept | path | fragment
```

Minimal workflow:

```text
1. Planner node
   -> creates article/page outline

2. Source node
   -> reads Ontogony source files through MCP/tool client

3. Writer node
   -> drafts page content using Conexus

4. Critic node
   -> scores clarity, rigor, hallucination risk, style fit

5. CMS formatter node
   -> outputs Astro/Tina-compatible markdown/frontmatter

6. Human approval
   -> user approves before writing to repo
```

## Primary outcome

A local run should produce an `AgentRun` containing:

```text
page_plan
source_bundle
source_manifest
draft
critique
cms_output
target_path
checkpoint
```

No repo file should be written until the checkpoint is approved.

## Non-goals

Do not implement A2A, persistent DB, agent memory, autonomous repo writes, self-improvement loops, background workers, vector search, full MCP registry, or broad generic framework abstractions.
