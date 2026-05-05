# 08 — Implementation Sequence

Use small commits.

## Commit 1 — Harden current Agentor spike

1. Add/confirm `AgentRun.next_node_index`.
2. Add/confirm `paused_at`.
3. Fix executor so awaiting approval does not set `finished_at`.
4. Add `resume()`.
5. Add tests for approval/resume behavior.

Acceptance:

```bash
cd agentor
pytest
```

## Commit 2 — Tool/MCP source reader

1. Replace vague `read_file` dependency with explicit `read_source_file`.
2. Add `SourceManifestItem` schema.
3. Root-restrict `FilesystemToolClient`.
4. Add tests for path traversal rejection.
5. Add tests for source bundle formatting.

## Commit 3 — Ontogony schema-aware formatter

1. Add `CmsCollection` enum/literal validation.
2. Add `build_frontmatter(collection, plan, critique)` helper.
3. Use YAML safe dump or robust escaping.
4. Add essay formatter first.
5. Add concept/fragment formatter optionally.
6. Add tests based on Ontogony schema.

## Commit 4 — Stronger critic

1. Add structured critic prompt.
2. Add JSON parser helper.
3. Store `critique` object with clarity, rigor, hallucination_risk, style_fit, overall.
4. Add malformed JSON fallback tests.

## Commit 5 — README and handoff

1. Update `agentor/README.md`.
2. Add example usage.
3. Add status: experimental v0.1 spike.
4. Document that Conexus M4 must exist for real runs.
