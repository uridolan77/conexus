# REASONS Canvas for Conexus

**Document path:** `/docs/specs/reasons-canvas.md`  
**Status:** Working template  
**Project:** Conexus  
**Last updated:** 2026-05-06

---

Use this canvas before non-trivial Conexus changes.

## R - Requirements

- What user-visible or operator-visible behavior must change?
- Which milestone or delivery slice does this support?

## E - Evidence

- What current code, docs, tests, logs, or KGB behavior show the problem or target behavior?

## A - Architecture

- Which Conexus layers are affected?
- Does the change cross the provider abstraction boundary, prompt registry boundary, or BO boundary?

## S - Scope

- What is in scope for this slice?
- What is explicitly out of scope so the work stays deployable?

## O - Operations

- Which validation commands prove the change?
- Are there migration, rollout, or environment implications?

## N - Naming

- Which API names, model identifiers, provider keys, trace fields, or BO labels are affected?

## S - Safety

- What could break?
- How is the change reversible?
- Which protected docs, secrets, or contracts must not be casually edited?