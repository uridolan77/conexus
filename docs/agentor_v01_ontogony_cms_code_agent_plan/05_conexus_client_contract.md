# 05 — Conexus Client Contract

Agentor must use Conexus for all model calls.

Endpoint:

```http
POST /v1/chat/completions
Authorization: Bearer <api_key>
Content-Type: application/json
```

Request:

```json
{
  "model": "conexus-smart",
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." }
  ],
  "temperature": 0.2,
  "max_tokens": 2048,
  "stream": false
}
```

Response shape:

```json
{
  "id": "chatcmpl_...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "conexus-smart",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "..." },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 200,
    "total_tokens": 300
  }
}
```

## Model aliases

Use aliases:

```text
conexus-fast  -> cheap/critic/simple JSON
conexus-smart -> planner/writer
```

## JSON robustness

Planner and critic ask for JSON, but LLMs may return invalid JSON.

Implement:

```python
parse_json_response(content, fallback)
```

Parser order:
1. direct `json.loads`
2. fenced json block
3. first `{...}` object
4. fallback with warning
