# 06 — Deployment

## Initial deployment

Deploy these early:

```text
backend API
frontend BO
PostgreSQL
logs
```

## Migrations (Alembic)

Conexus ships with Alembic migrations. **Production deployments should run migrations explicitly**.

Local (from repo root):

```text
cd backend
alembic upgrade head
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

## Future deployment plan (Vercel + subdomains)

### Frontend

- Deploy Next.js BO frontend to Vercel.
- Use a BO-focused subdomain such as `bo.<domain>` (for example `bo.conexus.<domain>`).

### Backend

- Do not deploy the current FastAPI backend to Vercel serverless by default.
- Prefer a container-friendly backend host such as Railway, Render, Fly.io, Azure Container Apps, or similar.
- Use an API-focused subdomain such as `api.<domain>`.

### Database

- Use managed PostgreSQL in production (Neon, Supabase, Railway Postgres, Render Postgres, or similar).

### Required production env vars

```text
APP_ENV=prod
DATABASE_URL=<managed postgres asyncpg url>
FRONTEND_BASE_URL=https://<frontend-subdomain>
BACKEND_BASE_URL=https://<api-subdomain>
NEXT_PUBLIC_BACKEND_BASE_URL=https://<api-subdomain>
AUTH_SECRET=<strong secret>
ADMIN_USERNAME=<admin username>
ADMIN_PASSWORD=<strong password or later hash>
ALLOW_ENV_ADMIN_FALLBACK=false
ENCRYPTION_KEY=<Fernet key>
```

Notes:

- Admin bootstrap: create the first admin in DB via CLI. Env fallback is intended for local/dev only.
- Schema: `create_all` is still used for local/dev convenience, but it is not a migration system. Use Alembic for deployments.
- Do not rotate `ENCRYPTION_KEY` casually; existing encrypted provider secrets require coordinated re-encryption.
- In prod, CORS must allow the frontend subdomain(s).
- Cookies must use `Secure=true` in prod, and same-site behavior must be validated across subdomains.

## Admin bootstrap (production)

After `alembic upgrade head`:

```text
cd backend
python -m app.cli create-admin --username admin --password <use_a_strong_password>
```

Alternative (non-interactive):

```text
cd backend
echo <use_a_strong_password> | python -m app.cli create-admin --username admin --password-stdin
```
