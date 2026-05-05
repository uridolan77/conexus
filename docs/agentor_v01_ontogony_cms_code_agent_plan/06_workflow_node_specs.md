# 06 — Workflow Node Specs

## 1. PlannerNode

Input: `topic`, `collection`

Output: `page_plan`, `target_path`

Responsibilities:
- create title
- create slug
- choose collection
- create thesis/summary
- create outline
- suggest cites and whereNext
- estimate reading time if essay

Validation:
- slug must be kebab-case
- collection must be supported
- title/summary/outline required

## 2. SourceNode

Input: `source_paths`, `source_query`, `page_plan`

Output: `source_bundle`, `source_manifest`

Responsibilities:
- read explicitly provided files through `ToolClient`
- optionally search sources through `search_sources`
- limit excerpts by char/token budget
- preserve source path metadata

## 3. WriterNode

Input: `page_plan`, `source_bundle`

Output: `draft`

Responsibilities:
- draft body only, no frontmatter
- use source material when available
- do not fabricate citations
- avoid over-marketing
- keep Ontogony conceptual tone

## 4. CriticNode

Input: `page_plan`, `source_bundle`, `draft`

Output: `critique`

Responsibilities:
- score clarity
- score philosophical/conceptual rigor
- score hallucination risk
- score Ontogony style fit
- list blocking issues
- list revision notes

## 5. CmsFormatterNode

Input: `page_plan`, `draft`, `critique`

Output: `cms_output`, `target_path`

Responsibilities:
- generate valid Astro/Tina frontmatter
- body remains markdown/MDX
- status is always draft
- use collection-specific frontmatter

## 6. ApprovalNode

Input: `cms_output`, `target_path`, `critique`

Output: `HumanApprovalCheckpoint`

Checkpoint prompt must show title, target path, collection, critic overall score, hallucination risk score, blocking issues, and preview.

No write should occur before approval.
