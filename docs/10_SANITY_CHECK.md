# 10 — Local Sanity Check (backend + BO)

This is a **fast smoke** to confirm the local stack is healthy and the BO basic flow works.

## Prereqs

- Docker Desktop running (WSL2 backend enabled).
- Ports available (or override in `.env`):
  - `POSTGRES_PORT` (default `5432`)
  - `BACKEND_PORT` (default `8000`)
  - `FRONTEND_PORT` (default `3000`)
- `.env` exists and includes a valid `ENCRYPTION_KEY` (Fernet).

## Start the stack

From repo root:

```powershell
docker compose up --build
```

Expected:

- Postgres becomes **healthy**
- Backend becomes **healthy**
- Frontend prints **Ready**

## Backend health

```powershell
$backendPort = 8000 # change if you overrode BACKEND_PORT in .env
$base = "http://localhost:$backendPort"
Invoke-RestMethod "$base/health" | ConvertTo-Json -Depth 10
Invoke-RestMethod "$base/readyz" | ConvertTo-Json -Depth 10
```

Expected:

- `/health` returns `status: ok`
- `/readyz` returns `status: ready` and `db/encryption/model_aliases: true`

## BO login (UI)

Open:

- BO: `http://localhost:3000/login` (change if you overrode `FRONTEND_PORT` in `.env`)

Login:

- `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env` (defaults `admin` / `admin`)

Expected:

- Redirect to `/` after login
- Sidebar renders (Projects / Providers / Requests / Usage / Routing / Smoke tests)

## BO basic features (UI)

### Projects + API keys

- Go to **Projects**
- Create a new project
- Issue a new project API key (copy the plaintext key shown once)

Expected:

- Project shows up in list
- Key shows with prefix + created time (plaintext only shown once)

### Providers

- Go to **Providers**
- Add a provider credential (OpenAI or Anthropic) and save
- Click **Test** on that provider

Expected:

- Provider row shows **active**
- Test result shows status + latency

Notes:

- If you use a placeholder key, **Test** will fail (that’s fine for UI sanity).
- For a full end-to-end success request, use a real upstream key (don’t commit it).

### Requests log

Make a gateway call using the project API key:

```powershell
$backendPort = 8000 # change if you overrode BACKEND_PORT in .env
$base = "http://localhost:$backendPort"
$projectKey = "<paste cx_live_...>"

Invoke-RestMethod `
  -Method Post `
  -Uri "$base/v1/chat/completions" `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $projectKey" } `
  -Body (@{
    model = "gpt-4o-mini"
    messages = @(@{ role = "user"; content = "Say hello from Conexus." })
  } | ConvertTo-Json -Depth 10)
```

Then in BO:

- Go to **Requests**
- Filter by the project you just created
- Open the latest request detail

Expected:

- A request row exists for your call
- If provider credentials are real + tested, the request should be `completed`
- If not, it may be `failed` with a useful `error_code`/`error_message` (still counts as logging sanity)

## Common local issues

- **Port already allocated**: set `POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT` in `.env`.
- **Backend crash: model aliases config not found**: backend image must include `static_config/model_aliases.yaml`.
- **502 / all_providers_failed**: no working provider credentials are configured (add one in BO and test it).

