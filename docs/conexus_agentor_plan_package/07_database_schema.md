# 07 — Database Schema

Use PostgreSQL. Prefer explicit relational columns for high-value query/filter fields; use JSONB only for flexible metadata.

## `organizations`

```sql
id uuid primary key
name text not null
created_at_utc timestamptz not null default now()
```

For v1 this can be a single default organization.

## `users`

```sql
id uuid primary key
organization_id uuid references organizations(id)
email text unique not null
password_hash text null
role text not null default 'owner'
is_active boolean not null default true
created_at_utc timestamptz not null default now()
last_login_at_utc timestamptz null
```

Can be simplified for early local auth.

## `projects`

```sql
id uuid primary key
organization_id uuid references organizations(id)
name text not null
slug text not null
status text not null default 'active'
created_at_utc timestamptz not null default now()
updated_at_utc timestamptz not null default now()
unique(organization_id, slug)
```

## `project_api_keys`

```sql
id uuid primary key
project_id uuid references projects(id)
name text not null
key_prefix text not null
key_hash text not null
status text not null default 'active'
last_used_at_utc timestamptz null
created_at_utc timestamptz not null default now()
revoked_at_utc timestamptz null
unique(key_prefix)
```

Suggested public key format:

```text
cx_live_<prefix>_<secret>
cx_test_<prefix>_<secret>
```

Hash only the full secret/key. Show it once.

## `llm_providers`

```sql
id uuid primary key
organization_id uuid references organizations(id)
provider_type text not null -- openai, anthropic, local, etc.
name text not null
status text not null default 'enabled'
secret_ref text null
api_base_url text null
default_timeout_ms int not null default 60000
metadata jsonb not null default '{}'
last_test_status text null
last_test_at_utc timestamptz null
created_at_utc timestamptz not null default now()
updated_at_utc timestamptz not null default now()
```

In early v1, provider keys can remain env-based; DB-backed secrets come later.

## `gateway_model_aliases`

```sql
id uuid primary key
organization_id uuid references organizations(id)
alias text not null -- conexus-fast, conexus-smart
primary_provider_id uuid references llm_providers(id)
primary_model text not null
fallback_provider_id uuid references llm_providers(id) null
fallback_model text null
temperature numeric(4,3) null
max_tokens_default int null
status text not null default 'active'
metadata jsonb not null default '{}'
created_at_utc timestamptz not null default now()
updated_at_utc timestamptz not null default now()
unique(organization_id, alias)
```

Static config can replace this in M3/M4; DB table becomes important in M5+.

## `gateway_requests`

```sql
id uuid primary key
request_id text unique not null
organization_id uuid references organizations(id)
project_id uuid references projects(id)
api_key_id uuid references project_api_keys(id)
model_alias text not null
provider_type text null
provider_model text null
status text not null -- started, completed, failed
http_status int null
latency_ms int null
prompt_tokens int not null default 0
completion_tokens int not null default 0
total_tokens int not null default 0
estimated_cost_usd numeric(12,6) not null default 0
fallback_used boolean not null default false
error_code text null
error_message text null
started_at_utc timestamptz not null default now()
completed_at_utc timestamptz null
metadata jsonb not null default '{}'
```

Indexes:

```sql
(project_id, started_at_utc desc)
(status, started_at_utc desc)
(provider_type, started_at_utc desc)
(model_alias, started_at_utc desc)
```

## `provider_attempts`

Optional but recommended once fallback is added.

```sql
id uuid primary key
gateway_request_id uuid references gateway_requests(id)
attempt_index int not null
provider_type text not null
provider_model text not null
status text not null -- completed, failed, skipped
latency_ms int null
prompt_tokens int default 0
completion_tokens int default 0
error_code text null
error_message text null
started_at_utc timestamptz not null default now()
completed_at_utc timestamptz null
metadata jsonb not null default '{}'
```

This makes fallback debugging much better in the BO.

## `usage_events`

```sql
id uuid primary key
gateway_request_id uuid references gateway_requests(id)
organization_id uuid references organizations(id)
project_id uuid references projects(id)
provider_type text not null
provider_model text not null
model_alias text not null
input_tokens int not null
output_tokens int not null
total_tokens int not null
cost_usd numeric(12,6) not null
created_at_utc timestamptz not null default now()
metadata jsonb not null default '{}'
```

## `audit_logs`

```sql
id uuid primary key
organization_id uuid references organizations(id)
actor_user_id uuid null references users(id)
actor_project_id uuid null references projects(id)
action text not null
resource_type text not null
resource_id text null
ip_address text null
user_agent text null
metadata jsonb not null default '{}'
created_at_utc timestamptz not null default now()
```

Use for provider key changes, API key creation/revocation, login/logout, and destructive admin actions.

## Schema cutline

Do not add these yet:

```text
budgets
semantic cache
prompt registry
adapter profiles
drift detection
A2A agent registry
memory store
workflow graph storage
```

Those are later Conexus/Agentor features.
