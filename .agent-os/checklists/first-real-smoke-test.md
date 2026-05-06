
# First Real Smoke Test Runbook

**Status:** Draft
**Project:** Conexus
**Scope:** First real gateway smoke test
**Purpose:** Provide a deterministic manual test proving Conexus can process a real LLM request and show it in the BO.

---

## 1. Goal

Prove the full M2/M3 path:

```text
backend healthy
→ BO login works
→ project exists
→ project API key exists
→ provider config exists
→ real /v1/chat/completions call succeeds
→ request is logged
→ request is visible in BO
```

---

## 2. Preconditions

### Infrastructure

* [ ] Backend is running.
* [ ] Frontend BO is running.
* [ ] Database is reachable.
* [ ] Migrations have been applied, or local `create_all` behavior is intentionally enabled.
* [ ] Backend `/health` responds.
* [ ] Backend readiness endpoint responds if available.

### Required Backend Environment

Confirm required env vars are set appropriately:

```text
APP_ENV
DATABASE_URL
AUTH_SECRET
ENCRYPTION_KEY
CORS_ALLOWED_ORIGINS or FRONTEND_ORIGINS
ALLOW_CREATE_ALL, depending on environment
ALLOW_ENV_ADMIN_FALLBACK, depending on environment
```

For production-like environments:

```text
APP_ENV=prod
ALLOW_CREATE_ALL=false
ALLOW_ENV_ADMIN_FALLBACK=false
COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS must not be '*'
```

### Secrets Safety

* [ ] No real provider API key is committed.
* [ ] `.env` is not committed.
* [ ] `ENCRYPTION_KEY` is set to a valid Fernet key.
* [ ] Provider secret is entered through the intended secure path.

### Admin Access

* [ ] Admin user exists in DB, or local fallback admin is intentionally enabled.
* [ ] Admin credentials are available to the tester.

---

## 3. Step 1 — Backend Health

Run:

```bash
curl -i http://localhost:8000/health
```

If readiness endpoint exists:

```bash
curl -i http://localhost:8000/health/ready
```

Expected:

```text
HTTP 200
service reports healthy
DB readiness passes if checked
```

Record result:

```text
PASS / FAIL:
Notes:
```

---

## 4. Step 2 — BO Login

Open:

```text
http://localhost:3000
```

Login as admin.

Expected:

```text
admin session established
BO dashboard or landing page loads
no auth loop
no browser console auth errors
```

Record result:

```text
PASS / FAIL:
Notes:
```

---

## 5. Step 3 — Create or Identify Project

In BO, create a project or identify an existing test project.

Recommended test project name:

```text
Smoke Test Project
```

Expected:

```text
project is created or visible
project id is available internally or in BO
```

Record:

```text
Project name:
Project id, if visible:
PASS / FAIL:
Notes:
```

---

## 6. Step 4 — Create Project API Key

Create a project API key for the smoke test project.

Recommended label:

```text
smoke-test-key
```

Expected:

```text
key is shown once
key can be copied
key is not visible in full after leaving the creation screen
```

Record:

```text
Key label:
Key copied: YES / NO
Secret later hidden: YES / NO
PASS / FAIL:
Notes:
```

Do not paste the real key into committed docs or chat logs.

---

## 7. Step 5 — Configure Provider

Create or identify an OpenAI provider config.

Runtime source rule for this smoke test:

```text
gateway resolves provider credentials BO-first (active provider_configs),
then falls back to env keys when BO config for a provider is missing/unusable.
```

Recommended label:

```text
openai-smoke-test
```

Expected:

```text
provider config saves successfully
provider secret is hidden after save
provider is enabled
model/default model is configured if required
gateway can use this BO provider config for real requests
```

If provider test exists, run it.

Expected provider test result:

```text
success, or safe actionable error
no secret leakage
```

Record:

```text
Provider label:
Provider type:
Model/default model:
Provider test PASS / FAIL / NOT AVAILABLE:
Notes:
```

---

## 8. Step 6 — Call Gateway

Use the project API key created in Step 4.

Notes:

```text
If an active BO provider config exists, the gateway should use it.
If BO config is missing/unusable, env key fallback may still be used.
```

Local example:

```bash
curl -i -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <project_api_key>" \
  -d '{
    "model": "conexus-fast",
    "messages": [
      {"role": "user", "content": "Say hello from Conexus in one short sentence."}
    ],
    "max_tokens": 80,
    "temperature": 0.2
  }'
```

If using a concrete OpenAI model instead of alias:

```bash
curl -i -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <project_api_key>" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Say hello from Conexus in one short sentence."}
    ],
    "max_tokens": 80,
    "temperature": 0.2
  }'
```

Expected response:

```text
HTTP 200
X-Conexus-Request-Id header present
response id present
choices[0].message.content present
provider present if response schema includes it
model present
usage present if provider returned usage
```

Record:

```text
HTTP status:
Request id:
Provider:
Model:
Usage present: YES / NO
PASS / FAIL:
Notes:
```

Do not paste the full provider response into committed docs if it contains sensitive content.

---

## 9. Step 7 — Verify Request Log

Verify the request was logged.

Use BO if available. Otherwise inspect DB through an approved local/dev method.

Expected request log state:

```text
request_id matches gateway response header
project_id is set
api_key_id is set
provider is set
model is set
status is completed
latency_ms is set
prompt_tokens/completion_tokens/total_tokens are set if available
estimated_cost is set if available
error_code is empty/null
error_message is empty/null
```

Record:

```text
Request log found: YES / NO
Status:
Latency:
Tokens:
Estimated cost:
PASS / FAIL:
Notes:
```

---

## 10. Step 8 — Verify BO Request Visibility

Open BO request list.

Expected:

```text
smoke-test request appears in list
status is visible
provider/model are visible
latency is visible
tokens/cost visible if available
```

Open request detail if available.

Expected:

```text
request id visible
project/api key metadata visible or inferable
provider/model visible
usage/cost visible when available
safe errors visible if failed
no secrets exposed
```

Record:

```text
Appears in request list: YES / NO
Request detail exists: YES / NO
Secrets hidden: YES / NO
PASS / FAIL:
Notes:
```

---

## 11. Negative Smoke Test — Invalid API Key

Run the same gateway request with an invalid project API key.

Expected:

```text
HTTP 401 or 403
safe error message
no provider call attempted
no secret leakage
```

Record:

```text
HTTP status:
PASS / FAIL:
Notes:
```

---

## 12. Negative Smoke Test — Unknown Model

Run the gateway request with an invalid model:

```json
{
  "model": "not-a-real-model",
  "messages": [
    {"role": "user", "content": "Hello"}
  ]
}
```

Expected:

```text
HTTP 400 or safe gateway error
request id present where possible
clear unknown model error
no raw stack trace
```

Record:

```text
HTTP status:
Request id:
PASS / FAIL:
Notes:
```

---

## 13. Pass / Fail Criteria

### Pass

The smoke test passes only if:

```text
1. Backend health passes.
2. BO login works.
3. Project exists.
4. Project API key works.
5. Provider config exists and is usable by runtime.
6. Real gateway call succeeds.
7. Request log is created.
8. Request is visible in BO.
9. Secrets are not exposed.
10. Invalid auth fails safely.
```

### Pass With Caveats

Allowed only if:

```text
real gateway call succeeds
request log is created
request is visible somehow, even if BO detail is incomplete
missing pieces are operator-facing polish, not core runtime blockers
```

### Fail

Fail if any of these occur:

```text
backend cannot start
BO login cannot work
project API key cannot be created or used
provider cannot be configured or used
provider is configured in BO but runtime does not use it
real gateway call fails due to runtime issue
request is not logged
request cannot be inspected at all
secrets are exposed
```

---

## 14. Smoke Test Result

```text
Date:
Environment:
Backend URL:
Frontend URL:
Tester:

Result:
[ ] Pass
[ ] Pass with caveats
[ ] Fail

Summary:

Smallest missing piece, if any:

Follow-up issue/slice:
```

---

## 15. Follow-Up Slice Template

If the smoke test fails or passes with caveats, define exactly one next slice:

```text
Title:

Goal:

Problem observed:

Smallest safe fix:

Files likely touched:

Acceptance criteria:

Validation commands:

Risks:
```
