Goal: continue developing core Conexus Gateway + Back Office production foundations, excluding the adaptation section.

Do not touch:
- /admin/adaptation/*
- frontend adaptation pages
- conexus.adaptation repo
- adapter profiles / adaptation runs / adaptation plans
- gateway publishing/canary/rollback

Focus:
- core gateway robustness
- provider configuration
- admin security
- auditability
- model alias configuration
- operational readiness
- BO quality-of-life improvements for non-adaptation areas

Current repo facts:
- FastAPI backend with `create_app()` and lifespan setup.
- Settings are in `backend/app/core/config.py` and currently include DB, backend/frontend URLs, admin auth, cookie policy, provider API keys, and `llm_provider`. :contentReference[oaicite:0]{index=0}
- Gateway endpoint is `/v1/chat/completions`.
- Gateway supports streaming and non-streaming responses.
- Gateway exception cleanup was already partly done:
  - `_to_chat_messages`
  - `_raise_gateway_http`
  - `ChatCompletionsResponse | StreamingResponse`
  - stream interruption logging
  - created timestamp captured at request start
- `gateway_router.py` already has `_Route = Literal[...]`.
- Admin auth, provider management, projects/API keys, requests, usage, routing, and audit endpoints already exist.
- Adaptation proxy exists but is out of scope for this prompt.

Implement the next core Conexus development slice.

============================================================
PHASE A — Provider timeout hardening
============================================================

1. Add explicit timeout settings.

In `backend/app/core/config.py`, add:

- `llm_request_timeout_seconds`
  - env alias: `LLM_REQUEST_TIMEOUT_SECONDS`
  - default: 60
  - must be >= 1

- `llm_stream_timeout_seconds`
  - env alias: `LLM_STREAM_TIMEOUT_SECONDS`
  - default: 180
  - must be >= 1

Update `.env.example`.

2. Apply timeouts to provider calls.

Preferred:
- Pass timeout to OpenAI/Anthropic SDK clients if supported cleanly.
- If SDK-level timeout is awkward or inconsistent, wrap calls with `asyncio.timeout(...)`.

Non-streaming:
- use `settings.llm_request_timeout_seconds`

Streaming:
- use `settings.llm_stream_timeout_seconds`

Timeout behavior:
- Provider timeout should become a provider-shaped error.
- Gateway should preserve existing external response behavior:
  - timeout should surface as current 502 upstream-style gateway error, unless existing tests expect another provider failure shape.
- Do not expose SDK timeout internals to clients.

3. Tests.

Add tests for:
- OpenAI chat timeout becomes `ProviderUnavailableError` or gateway-equivalent upstream error.
- Anthropic chat timeout becomes `ProviderUnavailableError` or gateway-equivalent upstream error.
- `/v1/chat/completions` timeout maps to existing gateway 502 shape.
- Streaming timeout yields controlled SSE error + `[DONE]` if timeout occurs after stream start.
- Timeout settings validate min value.

============================================================
PHASE B — Model alias configuration
============================================================

Current problem:
`gateway_router.py` hardcodes model aliases and model versions. Move those to static config.

1. Add file:

`backend/static_config/model_aliases.yaml`

Initial content must preserve current behavior:

```yaml
default_primary_model: claude-sonnet-4-20250514
default_fallback_model: gpt-4o

aliases:
  conexus-fast:
    anthropic: claude-haiku-4-5-20251001
    openai: gpt-4o-mini
  conexus-default:
    anthropic: claude-sonnet-4-20250514
    openai: gpt-4o
````

2. Add setting:

In `backend/app/core/config.py`:

* `model_aliases_path`

  * env alias: `MODEL_ALIASES_PATH`
  * default should work in local/backend runtime
  * prefer a path relative to backend root or repo root that is robust in tests

Update `.env.example`.

3. Add loader:

Create:

`backend/app/llm/model_alias_config.py`

Responsibilities:

* Load YAML.
* Validate required fields:

  * `default_primary_model`
  * `default_fallback_model`
  * `aliases`
* Validate each alias has:

  * `anthropic`
  * `openai`
* Reject blank model names.
* Reject duplicate/empty alias names.
* Return a typed object, e.g.:

```python
@dataclass(frozen=True)
class ModelAliasConfig:
    default_primary_model: str
    default_fallback_model: str
    aliases: dict[str, tuple[str, str]]
```

4. Update `gateway_router.py`.

Replace hardcoded aliases/defaults with loaded config.

Keep behavior:

* `conexus-default` resolves exactly as before.
* `conexus-fast` resolves exactly as before.
* Unknown aliases still raise `UnknownModelError`.
* Concrete `claude-*`, `anthropic-*`, `gpt-*`, `o1-*`, `openai-*` model names still route directly.
* `get_model_aliases()` still returns a copy.
* `get_known_provider_prefixes()` unchanged.

Do not add DB-backed routing in this phase.

5. Tests.

Add tests:

* config file loads successfully
* missing file fails clearly
* invalid YAML fails clearly
* alias missing `anthropic` fails clearly
* alias missing `openai` fails clearly
* `conexus-default` resolves as before
* `conexus-fast` resolves as before
* unknown alias still raises `UnknownModelError`

============================================================
PHASE C — Admin login rate limiting
===================================

Goal:
Add basic BO login brute-force protection.

1. Add settings:

In `backend/app/core/config.py`:

* `admin_login_max_failures`

  * env alias: `ADMIN_LOGIN_MAX_FAILURES`
  * default: 5
  * min: 1

* `admin_login_window_seconds`

  * env alias: `ADMIN_LOGIN_WINDOW_SECONDS`
  * default: 600
  * min: 30

Update `.env.example`.

2. Add service:

Create:

`backend/app/services/admin_login_rate_limiter.py`

Behavior:

* Process-local in-memory rate limiter.
* Key by:

  * normalized username
  * client IP when available
* Allow `ADMIN_LOGIN_MAX_FAILURES` failed attempts per `ADMIN_LOGIN_WINDOW_SECONDS`.
* After threshold, login returns 429.
* Successful login clears failures for that key.
* Do not reveal whether username exists.
* Do not store passwords.
* Keep implementation simple; no Redis.

3. Wire into `backend/app/api/admin_auth.py`.

Before authentication:

* check if login is currently rate-limited
* if yes, return 429 with generic detail

On failed login:

* record failure
* return 401 or 429 depending on threshold behavior

On successful login:

* clear failure count for key

4. Tests.

Add tests:

* repeated bad login returns 401 until threshold
* after threshold returns 429
* successful login clears failure count
* username normalization works
* rate limiting does not reveal whether DB admin or env fallback was used
* client IP participates in key if testable

============================================================
PHASE D — Admin audit strengthening
===================================

Goal:
Make admin security-sensitive actions visible in audit logs.

1. Ensure audit logs exist for:

* admin login success
* admin login failure
* admin login rate-limited
* admin logout
* provider create
* provider revoke
* provider test
* project create
* project API key issue
* project API key revoke
* project limits update

If any already exist, do not duplicate.

2. Metadata rules.

For login events:

* include username attempted
* include admin_user_id if known
* include reason category:

  * `success`
  * `invalid_credentials`
  * `rate_limited`
  * `bootstrap_required`
* include no password
* include no secret
* include no API key
* sanitize free text

For provider events:

* include provider
* label
* key mask only
* never raw provider key

For project key events:

* include key prefix only
* never raw API key or secret hash

3. Tests.

Add tests:

* login success creates audit log
* login failure creates audit log without password
* rate-limited login creates audit log
* provider create audit has no raw secret
* project API key issue audit has no raw key

============================================================
PHASE E — Gateway request/usage BO improvements
===============================================

Goal:
Improve the existing Back Office request/usage review experience, excluding adaptation.

Inspect current frontend structure before coding.

1. Request list polish.

In the existing requests page:

* preserve existing filters
* add or improve columns for:

  * request id
  * project
  * API key prefix or id
  * requested model
  * served model
  * provider
  * status
  * latency
  * cost
  * created_at
  * fallback_used
* failed requests should be visually distinct
* request id should be copyable

2. Request detail panel/page.

If not already present, add a detail view or expandable row showing:

* request id
* project id/name
* API key id/prefix
* requested model
* served model
* provider
* fallback_used
* token usage
* estimated cost
* latency
* error code/message
* created_at
* request metadata if available

Do not display full prompt/response bodies unless already safely stored and intended for BO visibility.

3. Usage page polish.

Improve existing usage page:

* show totals by project
* show totals by provider
* show cost totals
* show token totals
* show daily breakdown if existing backend supports it
* do not add new analytics backend unless needed

4. Tests.

Add frontend tests if test framework exists:

* requests page renders mocked rows
* failed request is highlighted
* filters call expected query params
* request detail displays error fields

If no frontend test setup is stable, add minimal tests only and report limitation.

============================================================
PHASE F — Routing/model observability endpoint
==============================================

Goal:
Expose current gateway model routing config to BO/admin.

Add backend endpoint:

`GET /admin/routing/model-aliases`

Auth:

* `Depends(get_admin_session)`

Returns:

```json
{
  "default_primary_model": "...",
  "default_fallback_model": "...",
  "aliases": {
    "conexus-default": {
      "anthropic": "...",
      "openai": "..."
    }
  },
  "known_provider_prefixes": {
    "anthropic": ["claude-", "anthropic-"],
    "openai": ["gpt-", "o1-", "openai-"]
  }
}
```

Frontend:

* If there is an existing routing/settings page, add a small “Model Aliases” panel.
* If no natural page exists, skip frontend and document endpoint.

Tests:

* endpoint requires admin
* endpoint returns current aliases
* endpoint does not expose provider API keys

============================================================
PHASE G — Small code-quality cleanup
====================================

1. In `gateway.py`, annotate:

```python
def _raise_gateway_http(exc: Exception) -> NoReturn:
```

Import `NoReturn`.

2. Keep `_event_stream()` nested for now unless refactor is small.
   Do not over-refactor.

3. Avoid large rewrites of:

* `admin_requests.py`
* `admin_usage.py`

4. Do not add:

* MediatR-like abstractions
* CQRS framework
* Redis
* background workers
* global rate limiting middleware
* streaming fallback

============================================================
Public API compatibility constraints
====================================

Do not change:

* `/v1/chat/completions` URL
* request body shape
* non-stream response shape
* SSE chunk shape
* `[DONE]` behavior
* `X-Conexus-Request-Id`
* project API key auth format
* existing admin endpoint paths
* existing database tables unless migration is required for audit changes

Do not break existing tests.

============================================================
Checks
======

Run:

```bash
cd backend
pytest -q
ruff check
```

If frontend changed:

```bash
cd frontend
npm test -- --run
npm run build
```

Report:

* files changed
* settings added
* config files added
* endpoints added
* tests added/updated
* backend test results
* frontend test/build results if applicable
* any deviations from scope

Expected final state:

* provider calls have explicit timeouts
* model aliases are config-driven
* admin login has brute-force protection
* security-sensitive admin actions are audited
* BO has better visibility into non-adaptation gateway usage
* current routing/model alias config is visible to admins
* adaptation code and adaptation UI remain untouched

```

This version is intentionally bigger, but still bounded: it advances **core Conexus** without drifting into adaptation, publishing, or workflow orchestration.
```
