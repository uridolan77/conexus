# 08 — Testing

Focus tests on the gateway path.

## First tests

```text
health endpoint returns OK
OpenAI adapter maps response correctly
Anthropic adapter maps response correctly
provider failure normalizes error
fallback works
pricing calculation works
API key hash verification works
request log is created on success
request log is created on failure
```

## KGB tests

Look for existing KGB tests around:

```text
ConexusRouter
OpenAIRouter
provider fallback
pricing
token usage
```

Copy the behavior, not necessarily the exact test structure.

## Deployment smoke test

Once deployed:

```text
GET /health
POST /v1/chat/completions with test key
verify response
verify request log
```
