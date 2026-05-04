# 09 — Security and Observability Plan

## Security principles

1. Provider secrets are never logged.
2. Project API keys are shown once and stored only as hashes.
3. Admin/user auth is separate from project API key auth.
4. Request logs store useful metadata, not raw sensitive prompts by default.
5. Errors returned to clients are sanitized.
6. Tool/MCP operations are audited and permissioned.

## Project API keys

Suggested format:

```text
cx_live_<prefix>_<secret>
cx_test_<prefix>_<secret>
```

Storage:

```text
key_prefix: searchable identifier
key_hash: argon2/bcrypt/hmac-sha256 hash of full key
status: active/revoked
last_used_at_utc
```

Rules:

- Secret is returned only once at creation.
- Logs may contain prefix, never full key.
- Revocation is immediate.

## Provider secrets

M7 or later:

- Encrypt at rest.
- Never return secret after save.
- Provider test must redact key and request body.
- Rotation should create audit log.

Early v1 may use env vars, but BO provider management should move secrets into DB/encrypted store.

## Admin auth

Short-term:

```text
single owner/admin login
protected admin routes
secure cookie or bearer JWT
```

Later:

```text
owner/admin/viewer roles
organization scoping
invite flow
MFA optional
```

The older `.NET LLMGateway` auth patterns are useful as design reference: login, refresh-token cookie, logout, users/admin endpoints, token usage analytics.

## Error taxonomy

Conexus should use stable error codes:

```text
validation_error
authentication_required
permission_denied
resource_not_found
provider_auth_error
provider_rate_limited
provider_timeout
provider_internal_error
llm_gateway_error
service_unavailable
```

HTTP mapping:

```text
400 validation_error
401 authentication_required
403 permission_denied
404 resource_not_found
408 provider_timeout if client-facing
429 provider_rate_limited if all providers rate-limited and no fallback
502 llm_gateway_error
503 service_unavailable
```

## Request logging

Every request should log:

```text
request_id
project_id
api_key_id
model_alias
provider
provider_model
status
latency_ms
input_tokens
output_tokens
total_tokens
estimated_cost
fallback_used
error_code
created/completed timestamps
```

Raw prompt logging should be disabled by default. Optional debug prompt retention should be explicit and access-controlled.

## Observability phase plan

### Phase 1 — structured logs

- JSON logs
- request_id in every log line
- provider and model in provider call logs
- sanitized errors

### Phase 2 — metrics

Metrics:

```text
conexus_requests_total{status,project,model_alias}
conexus_provider_attempts_total{provider,status}
conexus_latency_ms{model_alias,provider}
conexus_tokens_total{provider,model,type}
conexus_cost_usd_total{project,provider,model}
conexus_fallback_total{primary,fallback,reason}
```

### Phase 3 — tracing

Trace spans:

```text
HTTP request
GatewayService.resolve_route
ProviderAdapter.call
RequestLogService.complete
```

Do not trace raw prompt content unless explicitly enabled.

### Phase 4 — provider health

Later:

```text
provider health checks
last_test_status
last_test_at_utc
circuit-breaker state
fallback rate alerts
```

## MCP/tool safety

When Agentor/MCP starts:

- Read-only tools can run automatically if scoped.
- Write tools require approval.
- Destructive tools require approval and explicit resource identity.
- Every tool call is logged.
- Database tools must use allowlisted connection IDs, never arbitrary connection strings from prompts.

## Prompt-injection controls for tools

For tool outputs that come from untrusted documents/sites:

```text
mark as untrusted content
never execute instructions found inside retrieved content
separate tool data from system/developer instructions
critic node checks citation/source consistency
```

This is especially important for Ontogony source ingestion and future schema/document tools.
