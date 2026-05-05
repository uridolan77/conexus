# 09 — Testing Acceptance

## Unit tests

### ConexusClient
- success
- bearer auth header
- HTTP 401
- HTTP 502
- malformed response
- network error

### NodeExecutor
- normal run completes
- node failure marks failed
- checkpoint pauses
- paused run has `paused_at`, no `finished_at`
- approval resume continues
- rejection resume marks rejected
- previous nodes are not re-run on resume

### ToolClient
- reads allowed file
- rejects path traversal
- rejects absolute outside-root path
- handles missing file
- returns structured ToolResult

### OntogonyCmsWorkflow
- completes with auto approve
- pauses without auto approve
- includes source content
- creates essay frontmatter compatible with schema
- critic JSON parsed
- malformed planner JSON fallback
- malformed critic JSON fallback
- no write occurs before approval

### CMS formatter
- essay frontmatter valid
- concept frontmatter valid if implemented
- fragment frontmatter valid if implemented
- YAML-safe title/summary
- target path uses slug

## Integration smoke

With local Conexus running:

```bash
cd agentor
python examples/run_ontogony_cms.py \
  --topic "Closure-Crisis Lemma" \
  --collection essay \
  --source ../ontogony-site/src/content/concepts/closure.mdx
```

Expected:
- prints target path
- prints critic scores
- writes nothing
- displays approval checkpoint
