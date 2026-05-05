Agentor v0.1 Audit Report
Tests: 21 passed, 1 skipped — all green.

What exists vs. target
Target node	Status	Notes
Planner node	Partial match	PlanPageNode exists. Calls Conexus, returns {title, thesis, outline}. Missing: slug, summary, register, cites, whereNext from the full planner schema. JSON fallback is naive (no fenced-block extraction).
Source node via tool client	Partial match	GatherSourcesNode exists, calls tool.invoke("read_file", path=…). Works. Missing: search_sources, list_collection named tool methods; no read_source_file semantic distinction from generic read_file; StubToolClient.register is keyed only by tool name, so multiple read_file calls for different paths all return the same stub result.
Writer node via Conexus	Present	WriteDraftNode calls conexus.chat() correctly. Functionally complete for v0.1.
Critic node with multi-dim scoring	Mismatch	CritiqueDraftNode returns {score (0-10), notes}. Target requires: {clarity, rigor, hallucination_risk, style_fit, overall, blocking_issues, revision_notes, approved_for_human_review}. Current schema is a single integer + list.
Astro/Tina CMS formatter	Incomplete	FormatCmsNode only emits title, description, draft: true. Missing: slug, status, summary, register, readingTime, cites, whereNext, createdAt, updatedAt. No YAML-safe serialization (TODO comment acknowledges this). No src/content/essays/{slug}.mdx target path in output.
Human approval before write	Present	ApprovalNode installs a HumanApprovalCheckpoint. Executor pauses correctly. Works.
Resume after approval	Not implemented	One skipped test test_resume_after_approval_continues_remaining_nodes documents the gap. The executor has no resume() method; the only workaround is auto_approve=True on a full re-run. AgentRun has no next_node_index / paused_at fields.
Exact files/functions to change
1. agentor_runtime/workflows/ontogony_cms.py — critique_draft

Change the critic system prompt and expected JSON schema to the full 7-key schema (clarity, rigor, hallucination_risk, style_fit, overall, blocking_issues, revision_notes, approved_for_human_review).
Replace json.loads() fallback with a robust parse_json_response helper.
2. agentor_runtime/workflows/ontogony_cms.py — plan_page

Extend the planner prompt to also return slug, summary, register, cites, whereNext.
Use the same parse_json_response helper.
3. agentor_runtime/workflows/ontogony_cms.py — format_cms

Replace the f-string frontmatter with yaml.safe_dump or a proper YAML builder.
Emit the full essay schema fields, all as draft status.
Add target_path = src/content/essays/{slug}.mdx to state.
4. agentor_runtime/clients/tool.py — FilesystemToolClient

Add read_source_file(path), search_sources(query, limit), list_collection(collection) as named tools.
Update GatherSourcesNode to call read_source_file instead of generic read_file.
5. agentor_runtime/models.py — AgentRun

Add next_node_index: int = 0 and paused_at: datetime | None = None fields.
Confirm started_at, finished_at, checkpoint, error, duration_ms, is_terminal are all present (currently they are, checked in executor tests).
6. agentor_runtime/executor.py — NodeExecutor

Add resume(run) method that re-enters execution at run.next_node_index.
Track next_node_index when pausing at checkpoint.
Stamp run.paused_at when entering AWAITING_APPROVAL.
7. tests/test_executor.py

Unskip/implement test_resume_after_approval_continues_remaining_nodes.
Add tests: approve-then-resume, reject-then-resume, timing semantics (no finished_at while paused).
8. tests/test_ontogony_workflow.py

Add tests for: new critic schema keys, new planner schema keys, YAML frontmatter correctness (quotes, colons, arrays), target path in state, malformed JSON fallback.
Minor issues noted
FormatCmsNode has a self-acknowledged # TODO(#safe-frontmatter) comment — title/thesis double-quotes are stripped with .replace('"', "'") instead of proper YAML quoting.
StubToolClient stub keying by tool name only (not path) means test_workflow_includes_source_content only registers one response for read_file; multi-source tests would need a more capable stub.
No McpToolClient placeholder exists — only StubToolClient and FilesystemToolClient.
Completed: Report findings and gaps (6/6)

All 21 tests pass (1 skipped by design). The audit is complete — no files were modified. The table and file list above are the exact change targets for Prompts 2–5.