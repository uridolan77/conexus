# 07 — Database and Auth

## Database

Use PostgreSQL.

Keep schema simple and relational. Use `jsonb` only for flexible provider/request metadata.

## Naming

Use Postgres style:

```text
snake_case tables
snake_case columns
utc timestamps
```

Examples:

```text
gateway_requests
project_api_keys
created_at_utc
```

## API keys

Project API keys should be:

```text
generated securely
shown once
hashed in DB
identified by prefix
revocable
linked to project
```

Suggested format:

```text
cx_live_<prefix>_<secret>
```

## Provider secrets

Provider API keys should be:

```text
encrypted at rest
never returned after save
never logged
rotatable later
```

## Auth

For v1, choose the fastest reliable auth path:

```text
BO user login
protected admin routes
Owner/Admin/Viewer roles later if needed
```

Do not let auth delay the first deployed health/API skeleton.
