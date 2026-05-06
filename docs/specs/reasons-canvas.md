# REASONS Canvas for Conexus

**Document path:** `/docs/specs/reasons-canvas.md`  
**Status:** Working template  
**Project:** Conexus  
**Last updated:** 2026-05-06

---

Use this canvas before non-trivial Conexus changes.

## R - Requirements

What user-visible or operator-visible behavior change is needed? Which Conexus milestone or slice does this support?

## E - Evidence / Current Behavior / Examples

What current code, docs, tests, logs, or KGB behavior show the problem or target state? Cite concrete examples.

## A - Architecture / Boundaries

Which Conexus layers are affected? Does the change cross the provider abstraction boundary, prompt registry boundary, or BO boundary? What architectural constraints apply?

## S - Scope / Non-Goals

What is in scope for this slice? What is explicitly out of scope to keep the work deployable? What's a natural follow-up?

## O - Operations / Validation / Rollout

Which validation commands or tests prove the change? Are there migration, rollout, or environment implications? How do we know it's safe?

## N - Norms / Naming / Contracts

Which API names, model identifiers, provider keys, trace fields, or BO labels are affected? Are there naming conventions to respect?

## S - Safety / Security / Reversibility

- What could break?
- How is the change reversible?
- Which protected docs, secrets, or contracts must not be casually edited?