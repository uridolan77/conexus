# Provider abstraction (architecture entry point)

The full, normative specification for the provider adapter boundary lives here:

- `docs/specs/provider-abstraction.md`

That document is the **source of truth** for adapter responsibilities, normalized types, and what must not leak out of the gateway layer.

This file exists so architecture indexes and external readers can find the spec without duplicating its contents.

## Relationship to contracts

- HTTP/OpenAPI describes what cross-runtime clients send and receive (`contracts/openapi/conexus.v1.yaml`).
- Provider abstraction describes how Conexus talks to upstreams **inside** the Python service.

Do not place provider SDK types or vendor-specific DTOs in the .NET client; keep those concerns inside Conexus adapters as required by the spec above.
