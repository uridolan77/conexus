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

Use KGB’s router logic as the source:

- `ConexusRouter` for failover behavior
- `OpenAIRouter` for OpenAI request/usage mapping
- `LLMRouter` for Anthropic request/usage mapping
- `pricing.py` for token cost calculation
- `BaseLLMRouter` for interface shape

## V1 provider behavior

Start with OpenAI only:

```text
conexus-fast → configured OpenAI model
```

Then add Anthropic and fallback:

```text
primary provider fails with retryable error
→ fallback provider handles request
→ request log records fallback_used = true
```

## Request log fields

Capture:

```text
request_id
project_id
api_key_id
provider_id
model
status
latency_ms
prompt_tokens
completion_tokens
total_tokens
estimated_cost
error_code
error_message
fallback_used
created_at
completed_at
```

## Response compatibility

Be OpenAI-compatible enough that clients can change only:

```text
base_url
api_key
```

Full OpenAI compatibility can come later.
