# Operating Modes

- ASK: explain the current Conexus behavior, contracts, or architecture without editing files.
- PLAN: inspect the gateway, BO, or docs and propose the smallest Conexus slice to change.
- IMPLEMENT: make focused edits aligned to the current scope, provider abstraction, and deployable milestone.
- REVIEW: inspect changes for regressions, provider-boundary leaks, missing validation, or scope drift.
- DEBUG: reproduce a gateway or BO problem, isolate the owning layer, and fix it minimally.
- DOCUMENT: update the Conexus scope, architecture, provider spec, or operating docs without changing runtime code.
- RESCUE: stop broad or speculative work, identify drift from the current milestone, and simplify back to a deployable slice.

## Mode expectations

- Default to PLAN or DEBUG before IMPLEMENT when the owning layer is unclear.
- Use DOCUMENT when the code already matches the intended behavior but the source-of-truth docs drifted.
- Use REVIEW to check that provider SDK details remain isolated behind Conexus adapters.
- Use RESCUE when work starts turning into platform design instead of shipping the current gateway or BO milestone.
