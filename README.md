# Conexus

Conexus is a clean LLM gateway and monitoring back-office extracted from the useful LLM infrastructure already present in KGB.

The first target is simple:

```text
Admin login
→ configure provider
→ create project API key
→ call /v1/chat/completions
→ see request, provider, model, latency, tokens, cost, and errors in the BO
```

## Build strategy

This is not a theoretical rewrite. Start by harvesting the relevant LLM code from KGB, then simplify it into a standalone gateway.

Read first:

1. `docs/00_START_HERE.md`
2. `docs/01_KGB_REUSE_PLAN.md`
3. `docs/02_MILESTONES.md`
4. `docs/03_ARCHITECTURE.md`
5. `docs/04_GATEWAY.md`
6. `docs/05_BACK_OFFICE.md`
7. `docs/06_DEPLOYMENT.md`

## Main rule

Each milestone must run locally, deploy, and show its result in the BO or logs before the next milestone starts.

## Required runtime env

Backend startup requires `ENCRYPTION_KEY` to be set to a valid Fernet key.

- Missing key: settings validation fails at process start.
- Invalid key format: startup fails with a clear `invalid ENCRYPTION_KEY` error.

## Local Development

### 1) Install prerequisites

1. Install Docker Desktop for Windows (WSL2 backend enabled).
2. Install Python 3.12 locally for backend test/lint commands.
3. Ensure Node 20+ and npm are available for local frontend builds.

### 2) Create local `.env`

From the repo root:

```powershell
Copy-Item .env.example .env
```

Generate an encryption key and put it in `ENCRYPTION_KEY` inside `.env`:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Important:

- Do not commit real `ENCRYPTION_KEY` values.
- Do not commit provider API keys.

### 3) Start the local stack

From repo root:

```powershell
docker compose up --build
```

### 3A) Database migrations (recommended)

From repo root:

```powershell
cd backend
alembic upgrade head
```

Notes:

- Local/dev may still work without Alembic because the backend currently creates tables on startup for convenience.
- Production deployments should run Alembic migrations explicitly before starting the backend.

Open:

- frontend: http://localhost:3000
- backend: http://localhost:8000
- backend docs: http://localhost:8000/docs

### 4) Verify BO flow end-to-end

1. Open BO and login with local credentials from `.env`:
	 - `ADMIN_USERNAME=admin`
	 - `ADMIN_PASSWORD=admin`
2. Create a project in the Projects page.
3. Create a project API key (copy the key shown once).
4. Add a provider config in Providers page.
5. Use Test on that provider config to verify upstream connectivity.

### Admin bootstrap and env fallback

- Preferred (all environments): create admin users in DB:

```powershell
cd backend
python -m app.cli create-admin --username admin --password <strong_password>
```

- Env fallback is controlled by `ALLOW_ENV_ADMIN_FALLBACK`:
  - default **true** for non-prod environments
  - default **false** in `APP_ENV=prod`

### 5) Call gateway with project API key

Use the project API key returned by BO:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <project_api_key>" \
	-d '{
		"model": "gpt-4o-mini",
		"messages": [
			{"role": "user", "content": "Say hello from Conexus."}
		]
	}'
```

After a successful call, the request should be visible in BO request logs once that view is enabled for your milestone.

### 6) URL behavior in Docker Compose

- `DATABASE_URL` for backend containers must use host `postgres` (Docker service DNS).
- Browser calls must use `NEXT_PUBLIC_BACKEND_BASE_URL=http://localhost:8000`.
- Server-side frontend calls inside Docker use `BACKEND_BASE_URL=http://backend:8000`.

### 7) Troubleshooting

- Startup fails with `invalid ENCRYPTION_KEY`: generate a new Fernet key and update `.env`.
- Running backend directly (not in Docker): set `DATABASE_URL` host to `localhost`.
