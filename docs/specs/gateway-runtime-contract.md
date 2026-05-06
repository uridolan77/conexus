
# File 2: `docs/contracts/gateway-runtime-contract.md`

# Gateway Runtime Contract

**Status:** Draft
**Project:** Conexus
**Scope:** M2/M3 runtime contract
**Purpose:** Define the current expected behavior for gateway calls, request logging, provider configuration, and BO visibility.

---

## 1. Purpose

This contract defines what the current Conexus runtime must do before the first real smoke test.

It covers:

1. `/v1/chat/completions` behavior
2. request logging behavior
3. provider configuration behavior
4. BO request visibility behavior

This is not a future architecture document. It is a practical review contract for the current runtime.

---

## 2. Gateway Endpoint Contract

### Endpoint

```http
POST /v1/chat/completions
Authorization: Bearer <project_api_key>
Content-Type: application/json
```

### Minimal Request

```json
{
  "model": "conexus-fast",
  "messages": [
    {
      "role": "user",
      "content": "Say hello from Conexus."
    }
  ]
}
```

### Supported Request Fields for M2/M3

The runtime should support at least:

```text
model
messages
temperature
max_tokens
stream, if currently implemented
```

### Explicitly Unsupported or Limited

The runtime may reject or limit:

```text
tools
tool_choice
response_format other than text
logprobs
top_logprobs
n > 1
vision/image inputs
audio inputs
batching
```

Unsupported features should fail with a clear 4xx error and a request id when possible.

### Success Response Requirements

A successful non-streaming response should include:

```text
id
created
model
provider
choices
usage
request id in X-Conexus-Request-Id header
```

If runtime already includes `fallback_used`, preserve it.

### Error Response Requirements

Errors should include:

```text
stable error code
safe message
request_id where available
X-Conexus-Request-Id header where available
```

Errors must not expose:

```text
provider API keys
internal secrets
raw stack traces
full unredacted provider payloads
```

### Streaming Runtime Note

If streaming is already implemented, preserve current behavior.

For M2/M3, streaming is **present but not the hardening focus**. Do not remove or broadly refactor it unless explicitly requested.

Streaming hardening belongs to a later compatibility milestone.

---

## 3. Request Logging Contract

### Goal

Every gateway execution attempt should produce a durable request log record.

### Lifecycle

```text
1. Request received
2. Project API key authenticated
3. Request id created
4. Request log row started
5. Provider selected
6. Provider call attempted
7. Request log row completed or failed
8. Result visible to BO/operator
```

### Required Request Log Fields

A request log should include:

```text
request_id
project_id
api_key_id
provider
model
status
latency_ms
prompt_tokens
completion_tokens
total_tokens
estimated_cost
error_code
error_message
created_at
completed_at
fallback_used, if runtime supports it
gateway_profile_id, if runtime uses adapter profiles
```

### Success Case

After a successful request:

```text
status = completed
provider is set
model is set
latency_ms is set
prompt/completion/total tokens are set if provider returned usage
estimated_cost is set if pricing is available
error_code is empty/null
error_message is empty/null
```

### Failure Case

After a failed provider call:

```text
status = failed
provider/model are set when known
latency_ms is set
error_code is set
error_message is safe and operator-readable
request_id remains searchable
```

### Validation Failure Case

For request validation failures, define expected behavior clearly:

```text
Either:
- validation failures create request log rows

Or:
- validation failures do not create request log rows, but return request id and safe error
```

The review should record which behavior the current runtime uses.

### Streaming Case

If streaming is implemented:

```text
started row should be written before stream begins
completed row should be written when stream finishes successfully
failed row should be written on provider failure, timeout, or cancellation where possible
```

If current behavior differs, document it in the sanity review.

---

## 4. Provider Configuration Contract

### Goal

An admin can configure a provider in BO/admin API and make it usable by the gateway without exposing secrets.

### Provider Config Requirements

A provider configuration should support:

```text
provider key/name
display name or label
enabled/disabled state
secret/API key, encrypted or otherwise protected
default model or allowed model configuration
test-provider action, if implemented
created_at
updated_at
```

### Secret Handling

Provider secrets must obey:

```text
never committed
never returned in full after save
never shown in request logs
never shown in BO request details
encrypted at rest or protected by configured secret strategy
```

### Provider Test Behavior

If a provider test endpoint exists, it should:

```text
use the stored secret without exposing it
return success/failure safely
record enough error detail for admin debugging
avoid leaking raw provider secrets or stack traces
```

### Runtime Provider Selection

The review must identify the actual current path:

```text
Does gateway use env provider keys?
Does gateway use DB provider configs?
Does gateway use model aliases?
Does gateway use adapter profiles?
Does gateway use LLM_PROVIDER setting?
```

The sanity review should explicitly state the current behavior.

---

## 5. BO Request Visibility Contract

### Goal

After a gateway request, an operator can inspect what happened from the BO.

### Request List Requirements

The request list should show, where available:

```text
timestamp
project
api key label or masked id
provider
model
status
latency_ms
total tokens
estimated cost
error summary
fallback_used, if runtime supports it
```

### Request Detail Requirements

The request detail should show, where available:

```text
request_id
project/api key metadata
provider/model route
status
latency
usage/cost
error code/message
created/completed timestamps
gateway profile / adapter profile metadata, if used
```

### Data Safety

BO request visibility must not expose:

```text
provider API keys
project API key secrets
ENCRYPTION_KEY
AUTH_SECRET
raw sensitive request/response payloads unless explicitly enabled by policy
```

### Filtering Requirements

For M2/M3, minimal useful filters are:

```text
status
project
provider
model
date range
errors only
```

If filters are missing, record that as a follow-up, not necessarily a smoke-test blocker.

---

## 6. Fallback Runtime Note

If fallback is already present in the runtime, preserve it.

For M2/M3:

```text
fallback may exist
fallback may be inactive or not fully hardened
fallback is not the focus of the next slice
fallback behavior should not be removed casually
```

M6 should harden:

```text
fallback policy
fallback tests
fallback observability
fallback_used semantics
operator-facing fallback visibility
```

---

## 7. Acceptance for First Real Smoke Test

The runtime is ready for first real smoke test when:

```text
1. Admin can log into BO.
2. Admin can create or identify a project.
3. Admin can create a project API key.
4. Admin can configure or identify a usable provider.
5. A real /v1/chat/completions request succeeds.
6. The request creates a durable log row.
7. The request is visible in BO.
8. Secrets are not exposed.
9. Errors are safe and debuggable.
```

---

## 8. Review Questions

The sanity review must answer:

```text
1. What works right now?
2. What partially works?
3. What is missing?
4. What is misleading in docs?
5. What is the smallest missing piece before deployed smoke test?
6. Is the repo ready for a real smoke test?
```

---