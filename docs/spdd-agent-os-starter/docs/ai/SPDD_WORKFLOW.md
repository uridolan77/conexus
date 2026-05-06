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

REASONS = Requirements, Evidence, Architecture, Scope, Operations, Naming, Safety.
