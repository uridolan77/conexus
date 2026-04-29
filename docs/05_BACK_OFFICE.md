# 05 — Back Office

The BO should make the gateway easy to operate.

## Pages

```text
Login
Dashboard
Providers
Projects
Requests
Request Detail
Settings
```

## Dashboard

Show:

```text
requests today
success rate
failed requests
average latency
estimated cost
latest errors
```

## Providers

Admin can:

```text
add provider
save provider key
test provider
enable/disable provider
see last test status
```

## Projects

Admin can:

```text
create project
create API key
revoke API key
see project usage
```

## Requests

Show a table:

```text
time
request ID
project
provider
model
status
latency
tokens
cost
```

Request detail should show:

```text
routing decision
provider result
token usage
sanitized error
fallback status
trace/request ID
```

## Important UX rule

The BO is part of the product. Every backend capability should become visible there quickly.
