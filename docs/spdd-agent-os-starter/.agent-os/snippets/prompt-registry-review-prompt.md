# Prompt Registry Review Prompt

Use this prompt when reviewing changes to Conexus prompt registry functionality.

## Reviewer Prompt

```
You are reviewing changes to the Conexus prompt registry layer.

Confirm that the implementation satisfies these criteria:

VERSIONING & STATUS:
- [ ] Does the change preserve prompt versioning semantics (e.g., draft → active → deprecated)?
- [ ] Are version transitions enforced (can't jump directly from draft to deprecated)?
- [ ] Is the current/active prompt selection deterministic and testable?

VARIABLE SCHEMA:
- [ ] Are prompt variable schemas (name, type, required, description) validated on write?
- [ ] Can users query prompts by variable signature (useful for catalog/discovery)?
- [ ] Are variable naming conventions enforced (snake_case, no reserved names)?
- [ ] Are unused variables flagged or removed?

PROMPT RESOLUTION:
- [ ] Does prompt resolution (name + params) return the correct active version?
- [ ] Are resolution failures clear and traceable (prompt not found vs. version not found)?
- [ ] Is caching (if any) invalidated correctly on version changes?
- [ ] Can operators override resolution for emergency/canary scenarios?

TEMPLATE RENDERING:
- [ ] Does variable substitution work for system/user/assistant roles separately?
- [ ] Are missing required variables caught before render (not at runtime)?
- [ ] Are template syntax errors clear (not silent string replacement failures)?
- [ ] Does the renderer preserve message structure (no corruption of role/content/tool_call)?

USAGE TRACKING & TRACES:
- [ ] Are prompt usage events (name, version, variables, selected model) recorded in traces?
- [ ] Is the trace payload complete enough to reproduce the exact prompt sent?
- [ ] Can operators query "which prompts are in production" or "which prompts use this model"?
- [ ] Is PII (if any) in variable values redacted in traces?

OBSERVABILITY & METADATA:
- [ ] Are prompt metadata changes (status, description, owner) surfaced in the BO?
- [ ] Can operators drill down from a request trace to its prompt definition and version?
- [ ] Is prompt performance tracked (latency by prompt+model combination)?
- [ ] Are prompt-specific errors (resolution failure, template render failure) distinct in logs?

SCOPE BOUNDARIES:
- [ ] Does the change stay within prompt registry scope (version/variable/resolution)?
- [ ] Are provider-specific prompt optimizations (e.g., few-shot templates) documented as separate concerns?
- [ ] Is the registry agnostic to downstream routing/fallback logic?
- [ ] Does the change avoid coupling to Agentor or other external systems?

TESTS:
- [ ] Are unit tests present (versioning transitions, schema validation, variable substitution)?
- [ ] Are integration tests present (end-to-end resolution + render + trace)?
- [ ] Are negative cases tested (missing variables, invalid versions, resolve failures)?
- [ ] Do tests cover the BO query paths (if BO changes are included)?

REVERSIBILITY:
- [ ] Can this change be rolled back without data loss (e.g., new optional fields)?
- [ ] Are database migrations reversible?
- [ ] Is the change safe for gradual rollout (feature flag, if needed)?

MINIMAL & FOCUSED:
- [ ] Is the change limited to prompt registry (not mixing router, trace, or provider logic)?
- [ ] Are related concerns (prompt owner validation, approval workflow) captured as separate follow-ups?
- [ ] Does the PR description link follow-ups and risks?
```

## Integration Notes

- **When to use**: Before landing any PR that touches `backend/app/prompts/`, `backend/migrations/` (prompt_* files), or BO prompt UI
- **Paired with**: `docs/specs/provider-abstraction.md` (prompt registry sits outside provider boundary), `docs/product/conexus-v0-scope.md` (prompt registry is v0 feature)
- **Related slice checklist**: See `gateway-slice-checklist.md` for provider adapter reviews; use this prompt for prompt-registry-specific work
- **Follow-ups**: Prompt approval workflow, template syntax extensions, multi-language prompts are explicitly out of v0 scope

## Quick Checklist

If doing a focused prompt-registry PR, minimum checks:

1. ✅ Versioning/status transitions enforced
2. ✅ Variable schema validation on write
3. ✅ Prompt resolution deterministic and testable
4. ✅ Template rendering preserves message structure
5. ✅ Usage events recorded in traces
6. ✅ BO metadata queries work
7. ✅ Tests for negative cases (missing vars, invalid versions)
8. ✅ Change is reversible
9. ✅ Related concerns documented as follow-ups
10. ✅ Scope boundary respected (registry only, not router/provider/agent)
