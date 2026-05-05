# 03 — Architecture

## Shape

```text
Client / Agentor / KGB / CMS
        |
        v
Conexus API
        |
        +-- auth project API key
        +-- resolve provider/model
        +-- call provider adapter
        +-- write request log
        +-- write usage event when provider usage is complete
        |
        v
OpenAI / Anthropic / later providers

Admin BO
        |
        v
providers, projects, API keys, requests, usage, errors
```

The first useful product slice is an end-to-end operational loop:
create provider/project/key, call `/v1/chat/completions`, persist request
metadata, then inspect the call in the BO dashboard and request detail.

## Backend layout

```text
backend/
  app/
    main.py
    api/
      health.py
      gateway.py
      admin_dashboard.py
      admin_providers.py
      admin_projects.py
      admin_requests.py
      admin_usage.py
      admin_routing.py
      admin_audit.py
      auth.py
    core/
      config.py
      logging.py
    db/
      models.py
      session.py
      migrations/
    llm/
      base.py
      dependencies.py
      gateway_router.py
      model_alias_config.py  # runtime routing source for now
      openai_adapter.py
      anthropic_adapter.py
      pricing.py
      errors.py
    services/
      gateway_service.py
      provider_config_service.py
      project_key_service.py
      request_log_service.py
      usage_service.py
```

## Frontend layout

```text
frontend/
  app/
    login/
    page.tsx              # dashboard
    providers/
    projects/
    requests/
    usage/
    activity/
    limits/
    routing/
    adaptation/
  components/
  lib/
```

## Database core tables

```text
projects
project_api_keys
gateway_requests
usage_events
gateway_model_aliases
provider_configs
admin_users
audit_logs
project_limits
project_usage_windows
project_gateway_limit_reservations
gateway_adapter_profiles
gateway_adapter_profile_activations
```

Schema changes are represented by Alembic revisions. `create_all` remains a
local/dev convenience only; production should run migrations before startup and
set `ALLOW_CREATE_ALL=false`.

`gateway_model_aliases` is a persistence placeholder for BO/admin management in
the current M5/M6 slice. Runtime provider/model routing still uses the static
YAML/model-alias configuration by default; DB-backed alias routing is deferred so
existing boot and routing behavior does not change silently.

Provider configs are BO-managed encrypted credentials. Listing APIs return only
the provider, label, key mask, status, and test metadata; encrypted secrets stay
inside the service layer. Disabling a provider is terminal for now: it sets
`is_active=false` and `revoked_at`, removes the row from enabled-provider helper
results, and does not re-enable the same secret.

## Design preference

Start simple. Keep the gateway path clear before adding caching, broader runtime
provider configuration semantics, request correlation storage, distributed locks,
or tracing/metrics.
