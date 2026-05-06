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

### M2-M5: OpenAI primary, optional fallback

The gateway routes requests primarily through OpenAI:

```text
conexus-fast → configured OpenAI model
```

**Note on fallback:** The codebase includes fallback support (Anthropic secondary, OpenAI fallback), but this capability is not actively configured or hardened in M2-M5. Focus is on OpenAI stability. Fallback hardening and optimization are planned for M6.

### Runtime credential source (current)

Gateway provider credentials resolve with this precedence:

```text
1) BO provider config (active + not revoked) per provider
2) Environment provider key fallback
```

This means a saved BO provider config is used for real `/v1/chat/completions`
calls when present. Env keys remain a compatibility fallback for local/dev and
recovery scenarios.

### M6: Harden Anthropic/fallback behavior (later milestone)

In a future milestone, add:

```text
primary provider configuration and monitoring
fallback policy refinement and testing
request log recording of fallback_used
automatic fallback recovery patterns
```

**Note:** Fallback is present in the codebase but inactive by default. See `docs/product/conexus-v0-scope.md` for details. Do **not** refactor fallback logic unless explicitly asked; preserve existing behavior.

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

`fallback_used` is currently captured in request logs and returned in the
gateway response.

## Response compatibility

Be OpenAI-compatible enough that clients can change only:

```text
base_url
api_key
```

Full OpenAI compatibility can come later.

## Present but Not the M2/M3 Focus

The current runtime already contains extracted support for:
- streaming responses
- gateway fallback/failover
- `fallback_used` request/response metadata

For M2/M3:
- preserve existing behavior
- do not expand or refactor streaming/fallback unless explicitly requested
- focus on OpenAI stability, BO provider config, request logging, and BO request visibility

M6:
- harden Anthropic/fallback behavior
- refine fallback policy
- improve fallback observability
- test fallback paths deliberately

Later compatibility milestone:
- harden streaming behavior
- document exact OpenAI-compatible SSE behavior
- add stronger streaming tests

Other out-of-scope features for v0:
- Tool/function calling
- Response format / structured output
- Logprobs
- Multiple completions (n > 1)
- Vision / image inputs
- Request batching
