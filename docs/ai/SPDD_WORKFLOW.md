# SPDD Workflow

Structured-Prompt-Driven Development treats structured prompts, scope docs, and architecture boundaries as versioned engineering assets.

For Conexus, the flow should stay tied to a real vertical slice:

```text
Need -> REASONS Canvas -> Scope/spec check -> Small implementation slice -> Validation -> Doc sync
```

## Conexus workflow

1. Start with the delivery context in `docs/00_START_HERE.md` through `docs/06_DEPLOYMENT.md`.
2. Check the package source-of-truth docs:
	- `docs/product/conexus-v0-scope.md`
	- `docs/architecture/architecture-principles.md`
	- `docs/specs/provider-abstraction.md`
	- `docs/specs/reasons-canvas.md`
3. Define the smallest safe slice. Typical slices are:
	- provider adapter normalization
	- prompt registry behavior
	- trace logging and usage capture
	- back-office request visibility
4. Implement the change without widening into unrelated platform work.
5. Run the smallest relevant validation commands.
6. Update the affected docs if the behavior or contract changed.

## Rule of thumb

If a change does not make the gateway path, trace path, or BO visibility clearer, smaller, or more reliable, it is probably outside the current slice.

## REASONS Canvas Definition

Use this across all Conexus feature work:

- **R** — Requirements: What user-visible or operator-visible behavior change is needed?
- **E** — Evidence / Current Behavior / Examples: What code, logs, or KGB behavior show the problem?
- **A** — Architecture / Boundaries: Which Conexus layers and boundaries are affected?
- **S** — Scope / Non-Goals: What is in scope? What is explicitly out of scope?
- **O** — Operations / Validation / Rollout: How do we validate? Are there migration implications?
- **N** — Norms / Naming / Contracts: Which API names, trace fields, or BO labels change?
- **S** — Safety / Security / Reversibility: Is the change safe, reversible, and secure?
