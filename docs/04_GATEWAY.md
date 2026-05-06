# 04 — Gateway

## Endpoint

```http
POST /v1/chat/completions
Authorization: Bearer <project_api_key>
```

## Minimal request

```json
{
  "model": "conexus-fast",
  "messages": [
    { "role": "user", "content": "Hello" }
  ]
}
```

## Internal flow

```text
create request_id
authenticate project API key
validate request
resolve model alias
select provider
write gateway_requests row: started
call provider adapter
normalize response/error
update gateway_requests row: completed/failed
return response
```

## KGB code to reuse

For M1 (extract core), extract from KGB's router logic:

- `BaseLLMRouter` for interface shape
- `OpenAIRouter` for OpenAI request/usage mapping
- `pricing.py` for token cost calculation (basic, v0-scoped only)

For M6 (add Anthropic/fallback), also extract:

- `ConexusRouter` for failover/fallback behavior
- `LLMRouter` for Anthropic request/usage mapping

## Provider behavior timeline

### M2-M5: OpenAI only

The gateway routes all requests through OpenAI:

```text
conexus-fast → configured OpenAI model
```

### M6: Add Anthropic and fallback (later milestone)

In a future milestone, add:

```text
primary provider fails with retryable error
→ fallback provider handles request
→ request log records fallback_used = true
```

**Note:** Fallback (automatic retry with a different provider) is out of scope for v0. See `docs/product/conexus-v0-scope.md` for details.

## Request log fields

Fields to capture in v0 (OpenAI only):

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
```

**Note:** The `fallback_used` field will be added in M6 when fallback is implemented.

## Response compatibility

Be OpenAI-compatible enough that clients can change only:

```text
base_url
api_key
```

Full OpenAI compatibility can come later.

## Out of Scope for v0

**Streaming:** The endpoint returns a complete response in one call. Server-sent events (SSE) / streaming responses are out of v0 scope. See `docs/product/conexus-v0-scope.md` for details.

Other out-of-scope features:
- Tool/function calling
- Response format / structured output
- Logprobs
- Multiple completions (n > 1)
- Vision / image inputs
- Fallback / failover
- Request batching

These can be added in later milestones once the core gateway is stable.
