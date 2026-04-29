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
        |
        v
OpenAI / Anthropic / later providers

Admin BO
        |
        v
providers, projects, API keys, requests, usage, errors
```

## Backend layout

```text
backend/
  app/
    main.py
    api/
      health.py
      gateway.py
      admin_providers.py
      admin_projects.py
      admin_requests.py
      auth.py
    core/
      config.py
      security.py
      logging.py
    db/
      models.py
      session.py
      migrations/
    llm/
      base.py
      provider_factory.py
      openai_adapter.py
      anthropic_adapter.py
      pricing.py
      errors.py
    services/
      gateway_service.py
      provider_service.py
      project_key_service.py
      request_log_service.py
```

## Frontend layout

```text
frontend/
  app/
    login/
    dashboard/
    providers/
    projects/
    requests/
  components/
  lib/
```

## Database core tables

```text
users
organizations
projects
project_api_keys
llm_providers
llm_models
gateway_requests
usage_events
audit_logs
```

## Design preference

Start simple. Make the gateway path clear before adding caching, advanced routing, budgets, or streaming.
