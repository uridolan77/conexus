# 10 — Code-Agent Prompts

## Prompt 1 — Audit current Agentor spike

```text
You are working in the conexus repo on the Agentor v0.1 spike.

Audit only the `agentor/` package.

Goal: verify current behavior before changing anything.

Tasks:
1. Inspect README, models, executor, clients, workflow, tests.
2. Identify mismatches with this target:
   - Planner node
   - Source node through MCP/tool client
   - Writer node through Conexus
   - Critic node with clarity/rigor/hallucination/style scoring
   - Astro/Tina CMS formatter
   - Human approval before write
3. Run tests if possible.
4. Report exact files/functions to change.
5. Do not modify files yet.
```

## Prompt 2 — Implement approval resume safely

```text
Implement minimal approval resume in `agentor/`.

Requirements:
- Add `next_node_index` and `paused_at` to AgentRun if missing.
- Executor must not set `finished_at` when status is AWAITING_APPROVAL.
- Add `resume(run)` to continue after approved checkpoint.
- Rejected checkpoint marks run REJECTED.
- Do not re-run nodes before the checkpoint.
- Add/adjust tests for pause, approve-resume, reject-resume, and timing semantics.

Keep changes small. Do not touch Conexus backend/frontend.
```

## Prompt 3 — Harden source tools

```text
Harden Agentor tool access.

Requirements:
- Keep ToolClient minimal.
- Add explicit read-only tools:
  - read_source_file(path)
  - search_sources(query, limit)
  - list_collection(collection)
- Update Source node to use read_source_file, not generic read_file.
- FilesystemToolClient must be root-restricted and reject path traversal.
- Add tests for allowed read, missing file, traversal rejection, outside-root rejection.

Do not implement real MCP network client yet. Add a placeholder McpToolClient interface only if useful.
```

## Prompt 4 — Implement Ontogony schema-aware formatter

```text
Implement Astro/Tina-compatible frontmatter generation for Ontogony CMS.

Use the schema from ontogony-site:
- essays require title, summary, status; optional date, register, readingTime, cites, whereNext, createdAt, updatedAt.
- concepts require title, short, register, status, arrays for related/genealogy/notThis/whereNext.
- fragments require optional title plus status/createdAt/updatedAt.

For v0.1, fully support essay. Add concept/fragment only if small.

Rules:
- generated status is always draft.
- use YAML safe serialization or robust escaping.
- output target path is `src/content/essays/{slug}.mdx` for essays.
- add tests for quotes, colons, arrays, draft status, target path.
```

## Prompt 5 — Strengthen planner and critic JSON handling

```text
Improve PlannerNode and CriticNode.

Planner output schema:
{
  collection, title, slug, summary, thesis, register, outline, cites, whereNext
}

Critic output schema:
{
  clarity, rigor, hallucination_risk, style_fit, overall,
  blocking_issues, revision_notes, approved_for_human_review
}

Add a robust `parse_json_response` helper:
1. direct json.loads
2. fenced json block
3. first object extraction
4. fallback with warning

Add tests for malformed JSON fallback.
```

## Prompt 6 — Final v0.1 docs and example

```text
Finalize Agentor v0.1 docs.

Add:
- example script to run Ontogony CMS workflow with mock or real Conexus
- README usage
- clear warning: no files are written before approval
- note that real writes/PRs are v0.2
- explain required Conexus endpoint `/v1/chat/completions`

Run tests. Provide summary and exact changed files.
```
