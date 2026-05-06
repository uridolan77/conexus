# Conexus Architecture Principles

**Document path:** `/docs/architecture/architecture-principles.md`  
**Status:** Draft v0.1  
**Project:** Conexus  
**Last updated:** 2026-05-06

---

## 1. Purpose

These principles keep Conexus small, deployable, and extensible while the product is still proving its first production slice.

---

## 2. Core Principles

### 2.1 Small Deployable Vertical Slices

Every milestone should improve a working slice of the gateway or back office. Avoid speculative framework work that does not tighten the request path, trace path, or BO visibility.

### 2.2 Provider Isolation Is Mandatory

Provider SDKs and provider-specific payloads must stay behind the provider abstraction. The gateway, prompt registry, trace logging, and BO must work with normalized Conexus contracts.

### 2.3 Extract Before Inventing

When Conexus needs gateway behavior that already exists in KGB, prefer extracting and simplifying that code before inventing a new subsystem.

### 2.4 Conexus Does Not Depend on Agentor

Agentor and future orchestration systems may call Conexus, but Conexus must remain a stable lower-level service. Dependency direction stays:

```text
Agentor -> Conexus
```

### 2.5 Observability Is Part of the Product

Request logging, latency, token usage, cost estimation, and failure visibility are not optional instrumentation. They are part of the Conexus product contract.

### 2.6 Docs Define Boundaries

If code changes a product boundary, request contract, provider behavior, or operational expectation, update the matching scope, architecture, or spec document in the same slice.

---

## 3. Boundary Map

```text
client application
  -> Conexus API
  -> request validation
  -> prompt/template resolution
  -> model routing
  -> provider adapter
  -> provider SDK/API
  -> normalized response
  -> trace and usage logging
  -> back-office visibility
```

Allowed dependencies should flow downward through those layers. Provider-specific concerns must not leak upward into API, BO, or prompt-management surfaces.

---

## 4. Current Architectural Focus

The current Conexus focus is:

- a stable `/v1/chat/completions` path
- at least one solid provider adapter, OpenAI first
- normalized request and response models
- trace persistence in the database
- a useful BO request log view

Anything broader must justify itself against this slice.