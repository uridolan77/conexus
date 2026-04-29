# 06 — Deployment

## Initial deployment

Deploy these early:

```text
backend API
frontend BO
PostgreSQL
logs
```

## Environments

```text
local
staging
production
```

## Local stack

```text
docker-compose:
  postgres
  backend
  frontend
```

Redis can wait.

## Health endpoints

```http
GET /health
GET /health/ready
```

## Smoke test

Every deployed milestone should have a simple smoke test:

```text
health endpoint works
BO loads
DB reachable
gateway request works when milestone supports it
request appears in DB/BO when milestone supports it
```

## First deployment target

The first deployment does not need auth or gateway.

It only needs:

```text
API health
BO shell
DB connection
logs
```
