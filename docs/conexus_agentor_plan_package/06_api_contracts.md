# 06 — API Contracts

## Public gateway endpoint

### `POST /v1/chat/completions`

OpenAI-compatible enough that clients can change only `base_url` and `api_key` for basic non-streaming chat.

Request:

```json
{
  "model": "conexus-fast",
  "messages": [
    { "role": "system", "content": "You are helpful." },
    { "role": "user", "content": "Hello" }
  ],
  "temperature": 0.2,
  "max_tokens": 1024,
  "stream": false
}
```

Response:

```json
{
  "id": "chatcmpl_cx_...",
  "object": "chat.completion",
  "created": 1710000000,
  "model": "conexus-fast",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 4,
    "total_tokens": 16
  }
}
```

Headers:

```http
Authorization: Bearer cx_live_<prefix>_<secret>
```

## Error envelope

```json
{
  "error": {
    "code": "llm_gateway_error",
    "message": "All configured providers failed",
    "details": {
      "request_id": "...",
      "provider_errors": [
        { "provider": "anthropic", "code": "rate_limit" },
        { "provider": "openai", "code": "internal_server_error" }
      ]
    }
  }
}
```

Sensitive provider messages should be sanitized. Never expose provider API keys, raw stack traces, full prompts by default, or connection strings.

## Internal contracts

### `Message`

```python
class Message(TypedDict):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
```

### `TokenUsage`

```python
class TokenUsage(TypedDict, total=False):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    provider: str
    model: str
    cache_creation_tokens: int
    cache_read_tokens: int
```

### `ProviderRequest`

```python
@dataclass
class ProviderRequest:
    request_id: str
    messages: list[Message]
    model: str
    temperature: float = 0.2
    max_tokens: int = 1024
    tools: list[dict] | None = None
```

### `ProviderResponse`

```python
@dataclass
class ProviderResponse:
    content: str
    provider: str
    model: str
    usage: TokenUsage
    raw_finish_reason: str | None = None
    raw_response_id: str | None = None
```

### `GatewayResult`

```python
@dataclass
class GatewayResult:
    content: str
    model_alias: str
    provider: str
    provider_model: str
    usage: TokenUsage
    estimated_cost: Decimal
    fallback_used: bool
    provider_attempts: list[ProviderAttempt]
```

## Admin API

### `GET /admin/dashboard/summary`

Returns:

```json
{
  "requests_today": 34,
  "success_rate": 0.97,
  "failed_requests": 1,
  "average_latency_ms": 1280,
  "estimated_cost_today": 0.42,
  "latest_errors": []
}
```

### `GET /admin/requests`

Query params:

```text
status
project_id
provider
model
from
until
limit
offset
```

### `GET /admin/requests/{request_id}`

Returns request detail including sanitized prompt metadata, provider attempts, usage, cost, fallback, error, and timings.

## Provider management API

Later milestone:

```http
GET /admin/providers
POST /admin/providers
POST /admin/providers/{id}/test
PATCH /admin/providers/{id}
```

Saved provider secrets must never be returned after save.

## Project API key API

```http
POST /admin/projects
GET /admin/projects
POST /admin/projects/{id}/api-keys
POST /admin/projects/{id}/api-keys/{key_id}/revoke
```

API key response shows secret only once.
