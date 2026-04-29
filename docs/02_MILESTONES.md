# 02 — Milestones

Keep this sequence. Each step should deploy before the next starts.

## M0 — Blank repo boots

Deliver:

```text
FastAPI health endpoint
Next.js BO shell
PostgreSQL in docker-compose
basic CI
```

Acceptance:

```text
/health returns OK
BO loads
DB connection works
```

## M1 — Extract KGB gateway core

Deliver:

```text
provider interface
OpenAI adapter
Anthropic adapter
pricing helper
provider factory
unit tests copied/refactored from KGB behavior
```

Acceptance:

```text
mocked OpenAI call works
mocked Anthropic call works
fallback test works
cost calculation works
```

## M2 — First real gateway call

Deliver:

```text
POST /v1/chat/completions
project API key auth
OpenAI provider call
request log row
```

Acceptance:

```text
curl returns real model response
request appears in DB
latency/status/tokens recorded
```

## M3 — BO auth and provider config

Deliver:

```text
admin login
provider list
add provider key
test provider
```

Acceptance:

```text
admin can add/test OpenAI provider
provider secret is not shown after save
test result appears in BO
```

## M4 — Projects and API keys

Deliver:

```text
create project
create/revoke API key
project usage view
```

Acceptance:

```text
project key can call gateway
revoked key fails
usage is linked to project
```

## M5 — Request monitoring

Deliver:

```text
request list
request detail
filters
basic dashboard cards
```

Acceptance:

```text
admin can debug a successful or failed gateway call from BO
```

## M6 — Anthropic and fallback

Deliver:

```text
Anthropic provider
fallback policy
normalized errors
```

Acceptance:

```text
Anthropic failure can fall back to OpenAI
fallback is recorded in request detail
```
