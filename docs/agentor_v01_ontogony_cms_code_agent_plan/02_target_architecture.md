# 02 — Target Architecture

```text
OntogonyCmsWorkflow
  ├── PlannerNode
  ├── SourceNode
  ├── WriterNode
  ├── CriticNode
  ├── CmsFormatterNode
  └── ApprovalNode

NodeExecutor
  ├── runs nodes sequentially
  ├── records NodeOutcome
  ├── pauses on HumanApprovalCheckpoint
  └── resumes after approval

ConexusClient
  └── POST /v1/chat/completions

ToolClient / MCPToolClient
  ├── read_source_file
  ├── search_sources
  ├── list_collection
  ├── validate_slug_refs
  ├── run_ontogony_check later
  └── write_file / open_pr later, approval-gated
```

## Workflow state keys

Input:

```text
topic: str
collection: "essay" | "concept" | "path" | "fragment", optional default "essay"
source_paths: list[str], optional
source_query: str, optional
```

Produced:

```text
page_plan: dict
source_bundle: str
source_manifest: list[dict]
draft: str
critique: dict
cms_output: str
target_path: str
checkpoint: HumanApprovalCheckpoint
```

## Page plan schema

```json
{
  "collection": "essay",
  "title": "string",
  "slug": "string-kebab-case",
  "summary": "string",
  "thesis": "string",
  "register": "R1|R2|R3|R4|null",
  "outline": ["section heading"],
  "cites": ["concept-slug"],
  "whereNext": [
    {
      "kind": "concept|essay|path|diagram",
      "slug": "string",
      "title": "optional",
      "why": "optional"
    }
  ]
}
```

## Critique schema

```json
{
  "clarity": 0,
  "rigor": 0,
  "hallucination_risk": 0,
  "style_fit": 0,
  "overall": 0,
  "blocking_issues": ["string"],
  "revision_notes": ["string"],
  "approved_for_human_review": true
}
```

Score scale: 0-10. Hallucination risk is inverse: 0 means low risk, 10 means severe risk.
