# ADR-0003: Contract versioning policy

## Status

Proposed.

## Decision

Conexus HTTP routes use major API versions:

```text
/v1/...
```

The OpenAPI contract carries semantic contract version metadata:

```yaml
info:
  version: 1.0.0
```

The on-disk OpenAPI path is `contracts/openapi/conexus.v1.yaml`.

## Compatibility rules

Compatible changes:

- adding optional request fields
- adding response fields
- adding new endpoints
- adding enum values only when clients are resilient to unknown values

Breaking changes:

- removing fields
- renaming fields
- changing field meaning
- changing requiredness
- changing error shape for existing status codes
- changing route behavior in a way that breaks existing clients

## Required process

Every contract change should update:

- OpenAPI (`contracts/openapi/conexus.v1.yaml`)
- JSON schemas under `contracts/json-schema/`, where relevant
- examples under `contracts/examples/`
- .NET DTOs in `src/dotnet/Conexus.Client` when the public gateway shape changes
- contract tests under `backend/tests/test_contract_assets.py`
