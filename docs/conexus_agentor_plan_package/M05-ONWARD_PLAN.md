# Master guardrail prompt for every milestone

```text
You are working in the Conexus repo on the current main branch.

Important rules:
1. Treat main as the source of truth.
2. Do not rewrite architecture unless explicitly required.
3. Prefer small, safe, vertical-slice changes.
4. Keep Conexus deployable/runnable after each milestone.
5. Preserve existing tests unless they are objectively wrong.
6. Add regression tests for every behavior you touch.
7. Do not add speculative framework features.
8. Do not silently skip failing tests.
9. Avoid broad refactors.
10. If you find a blocker, document it clearly and propose the smallest safe fix.

Before coding:
- Inspect the relevant existing files.
- Identify what already exists.
- Identify the minimal missing pieces.
- Write a short implementation plan.

After coding:
- Run:
  python -m ruff check .
  python -m pytest -q

If the repo has multiple packages, run tests/checks in the affected package directories too.
Summarize:
- files changed
- behavior added
- tests added
- known limitations
```

---

# M5 — Persistence and project API keys hardening prompt

Use this even if M5 is “merged,” because this prompt is about **verifying and hardening** the merged state.

```text
Review and harden M5: Persistence and project API keys.

Context:
M5 is responsible for durable project-level gateway usage:
- projects
- project_api_keys
- provider/model/alias persistence where currently implemented
- gateway_requests
- usage_events
- audit_logs
- API key generation/hash/revoke
- success/failure request persistence
- usage/cost storage

Goal:
Make M5 production-safe enough that every successful or failed gateway request leaves a reliable audit trail and usage record.

Scope:
Only backend persistence/auth/gateway paths.
Do not implement BO UI.
Do not implement provider management UI.
Do not expand Agentor.

Step 1 — Inspect current implementation:
Check:
- backend/app/db/models.py
- backend/app/db/migrations/versions/*
- backend/app/services/project_key_service.py
- backend/app/services/gateway_service.py
- backend/app/services/request_log_service.py
- backend/app/services/usage_service.py if present
- backend/app/api/auth.py
- backend/app/api/gateway.py
- backend/tests related to gateway/auth/persistence

Step 2 — Verify schema completeness:
Confirm whether these exist:
- ProjectApiKey.last_used_at
- UsageEvent or equivalent durable usage table
- GatewayModelAlias or equivalent model-alias persistence
- GatewayRequest with request_id/project_id/api_key_id/provider/model/status/tokens/cost/error/timestamps
- AuditLog
- migrations for all added schema

If a required M5 item is missing, implement the smallest version that fits the current architecture.

Expected model behavior:
ProjectApiKey:
- last_used_at nullable datetime
- updated only after valid, non-revoked authentication
- preferably throttled so every request does not hot-write the same key row

UsageEvent:
- durable row for completed usage
- contains project_id, api_key_id, gateway_request_id/request_id, provider, model, requested_model, prompt_tokens, completion_tokens, total_tokens, estimated_cost, fallback_used, created_at
- must be idempotent: one usage event per gateway request
- enforce uniqueness at DB/model/service level

GatewayModelAlias:
- stores alias name, provider, concrete model, active flag, timestamps, metadata if current design supports DB aliases
- if alias config remains YAML-only, document the intentional cutline and do not partially implement unused DB alias tables

Step 3 — Auth hardening:
In project_key_service.verify_api_key:
- malformed key returns None
- unknown prefix returns None
- revoked key returns None
- invalid secret returns None
- valid key returns project and api_key
- last_used_at is updated only for valid, non-revoked key
- avoid high write pressure:
  - either update only if last_used_at is older than 60 seconds
  - or use a small helper update_api_key_last_used_at(session, api_key, now)

Tests:
- valid key authenticates
- revoked key fails and does not update last_used_at
- invalid secret fails and does not update last_used_at
- malformed key fails
- valid key updates last_used_at
- repeated valid verification within throttle window does not constantly change last_used_at

Step 4 — Gateway persistence hardening:
For non-streaming:
- start GatewayRequest before provider call
- on success, mark completed with provider/model/tokens/cost/fallback
- record exactly one UsageEvent on success
- on provider/client/upstream failure, mark failed with sanitized error
- no UsageEvent for failed request unless current design explicitly records failed zero-usage events

For streaming:
- start GatewayRequest before stream begins
- on normal stream completion, mark completed and record exactly one UsageEvent if final usage exists
- on mid-stream provider error, mark failed
- on timeout, mark failed
- on cancellation/client disconnect, mark terminal failed/cancelled/interrupted; do not leave status=started
- reconcile limit reservations in all terminal paths

Important:
asyncio.CancelledError may not be caught by except Exception. Add explicit handling where needed.

Tests:
- non-stream success logs request and usage event
- non-stream provider error logs failed request and no success usage event
- stream success logs request and usage event
- stream mid-error logs failed request
- stream cancellation/client disconnect does not leave request status=started
- duplicate record_usage_event for same gateway request is idempotent or rejected safely

Step 5 — Migration review:
Ensure latest migration:
- has correct revision/down_revision
- creates needed columns/tables/indexes/constraints
- has downgrade
- indexes common query paths:
  - gateway_requests.project_id + created_at
  - gateway_requests.api_key_id + created_at
  - usage_events.project_id + created_at
  - usage_events.gateway_request_id unique
  - project_api_keys.prefix unique
  - aliases active lookup if implemented

Step 6 — Run checks:
From backend:
python -m ruff check .
python -m pytest -q

Deliverable summary:
- What M5 had before
- What was fixed
- Whether usage_events and alias persistence are implemented or intentionally deferred
- Remaining risks
```

---

# M6 — Back-office shell and request visibility prompt

This is the actual M6 vertical slice: **admin can log in and see gateway requests**.

```text
Implement M6: BO shell and request visibility.

Context:
M6 should provide a minimal back-office UI and API surface for operational visibility:
- BO loads
- admin auth/session works enough for local use
- dashboard
- requests table
- request detail
- provider page stub
- projects page stub
- request detail shows provider/model/tokens/cost/status/fallback/error

Goal:
Build the smallest useful BO that lets me call /v1/chat/completions and then inspect the request in the UI.

Scope:
- Frontend BO shell if frontend app exists
- Backend admin/session/request visibility endpoints
- Tests for backend endpoints and critical UI behavior if test infrastructure exists

Do not:
- build full provider management yet
- build charts unless trivial
- add role-based permissions beyond existing simple admin concept
- implement complex filters beyond basic pagination/status/project query

Step 1 — Inspect current repo:
Find:
- frontend app location, package manager, routing approach
- backend admin auth endpoints
- backend request log models/services
- existing CORS/session/cookie settings
- any BO/dashboard files
- tests setup

Step 2 — Backend request visibility API:
Implement or verify endpoints:

GET /admin/requests
Query params:
- page
- page_size
- status optional
- project_id optional
- api_key_id optional
- provider optional
- model optional
- q optional request_id search
- from/to optional datetime if easy

Response:
{
  "items": [
    {
      "request_id": "...",
      "project_id": "...",
      "api_key_id": "...",
      "requested_model": "...",
      "provider": "...",
      "model": "...",
      "status": "completed|failed|started",
      "latency_ms": 123,
      "prompt_tokens": 10,
      "completion_tokens": 20,
      "total_tokens": 30,
      "estimated_cost": 0.001,
      "fallback_used": false,
      "error_code": null,
      "created_at": "...",
      "completed_at": "..."
    }
  ],
  "page": 1,
  "page_size": 25,
  "total": 123
}

GET /admin/requests/{request_id}
Response includes all request fields plus:
- error_message
- domain_key / gateway_profile_id / adapter_profile_id if present
- usage_event if present
- related project/key display info if cheap

Security:
- require admin/session auth
- do not expose API key secret hashes
- do not expose provider encrypted secrets

Tests:
- unauthenticated request returns 401/403
- authenticated admin can list requests
- pagination works
- request detail returns full details
- failed request includes sanitized error
- no secret fields leak

Step 3 — Backend dashboard summary API:
Implement or verify:

GET /admin/dashboard/summary

Return:
- total requests today
- completed requests today
- failed requests today
- started/stale requests count
- total estimated cost today
- total tokens today
- recent 10 requests
- provider breakdown if easy

Keep it simple. No heavy analytics.

Tests:
- seeded completed/failed requests produce correct summary
- empty DB returns zeros

Step 4 — BO frontend shell:
Implement minimal BO pages:

Routes:
- /login
- /
- /requests
- /requests/[request_id]
- /providers
- /projects

UI requirements:
- clean simple layout
- sidebar/nav
- top bar with current admin/logout if available
- dashboard cards
- requests table
- request detail page
- loading/error/empty states

Requests table columns:
- created_at
- status
- requested_model
- provider
- actual model
- total_tokens
- estimated_cost
- latency_ms
- fallback_used
- request_id shortened

Request detail sections:
- Overview
- Model routing
- Usage/cost
- Error details
- Raw identifiers

Step 5 — Local developer experience:
Add or update docs:
- how to start backend
- how to start BO/frontend
- how to create/seed admin user if needed
- how to generate a project API key
- how to make a test gateway call
- how to view the request in BO

Step 6 — Run checks:
Backend:
python -m ruff check .
python -m pytest -q

Frontend:
npm install if needed
npm run lint
npm test if present
npm run build

Deliverable summary:
- BO routes added
- backend admin endpoints added
- screenshots not required, but list pages
- tests added
- remaining M6 gaps
```

---

# M6B — Request visibility polish and operational filters prompt

Run this only after the basic M6 BO works.

```text
Polish M6 request visibility.

Goal:
Make the request visibility BO actually useful for debugging gateway behavior.

Scope:
Only request/dashboard visibility. Do not implement provider management yet.

Backend:
Enhance GET /admin/requests with:
- status filter
- provider filter
- requested_model filter
- date range filter
- fallback_used filter
- min_cost/max_cost optional if easy
- stable sort newest first
- page/page_size bounds

Add stale request detection:
- status=started and created_at older than configured threshold
- expose stale boolean in list/detail

Frontend:
Requests page:
- filter bar
- refresh button
- copy request_id button
- clear filters button
- status badges
- fallback badge
- error badge
- cost formatting
- token formatting

Request detail:
- highlight failure cause
- show timing
- show raw request_id
- show provider/model
- show usage/cost
- show linked usage event if implemented
- show reservation info if present

Tests:
- filters work independently
- filters combine correctly
- pagination stable
- stale detection works
- UI handles empty/filter-no-results state

Run:
python -m ruff check .
python -m pytest -q
frontend lint/build/tests as available
```

---

# M7 — Provider management prompt

```text
Implement M7: Provider management.

Context:
M7 adds provider secret management to the BO:
- add provider key
- encrypt provider secret
- test provider
- enable/disable provider
- rotate-key placeholder
- saved key is never returned

Goal:
Allow an admin to configure OpenAI/Anthropic provider keys from the BO and test them safely.

Scope:
- backend provider config model/service/API
- BO providers page
- tests
- do not build multi-tenant billing
- do not implement complex provider health scheduler yet

Step 1 — Inspect current provider config:
Check:
- ProviderConfig model
- provider_config_service
- secret_crypto/encryption
- provider test flow
- provider factory/dependency behavior
- existing BO provider page stub

Step 2 — Backend API:
Implement/verify endpoints:

GET /admin/providers
Return provider configs without secrets:
{
  "items": [
    {
      "id": "...",
      "provider": "openai|anthropic",
      "label": "...",
      "key_mask": "sk-...abcd",
      "is_active": true,
      "revoked_at": null,
      "last_test_status": "ok|failed|null",
      "last_test_error": null,
      "last_tested_at": "...",
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}

POST /admin/providers
Body:
{
  "provider": "openai|anthropic",
  "api_key": "...",
  "label": "Production OpenAI"
}
Behavior:
- validate provider enum
- encrypt secret
- store key_mask only
- never return plaintext or encrypted secret
- audit log provider_config.created

POST /admin/providers/{id}/test
Body:
{
  "model": "gpt-4o-mini" or "claude-haiku..."
}
Behavior:
- decrypt secret inside service only
- make minimal provider call
- store last_test_status, last_test_error, last_tested_at
- sanitize errors so secret never leaks

POST /admin/providers/{id}/disable
- set is_active=false
- set revoked_at
- audit log provider_config.disabled

POST /admin/providers/{id}/enable
- set is_active=true
- clear revoked_at if current design allows re-enable
- or reject if revoked configs are immutable; choose one and document

POST /admin/providers/{id}/rotate
- placeholder endpoint may return 501/not implemented
- or implement rotate by replacing encrypted key/key_mask and clearing test status
- choose smallest safe behavior

Security:
- no secret fields in API response
- no encrypted secret in API response
- sanitize provider errors
- require admin auth

Step 3 — Active provider resolution:
Ensure gateway provider factory can use active provider configs if that is already intended.
If current design still reads env vars only, do not silently change production routing.
Instead:
- implement read helper get_active_provider_config(provider)
- document whether gateway uses DB configs now or later
- if wiring DB configs into runtime is small and safe, do it behind a setting:
  PROVIDER_CONFIG_SOURCE=env|db
Default should preserve existing behavior unless docs say otherwise.

Step 4 — BO providers page:
Implement:
- list provider configs
- add provider form
- test provider button
- enable/disable button
- show key mask
- show last test status/error
- never show secret after save
- rotate placeholder or rotate form

Step 5 — Tests:
Backend:
- create provider stores encrypted secret and mask
- list provider does not expose api_key_encrypted
- test provider success updates status
- test provider failure stores sanitized error
- disable prevents active lookup
- unauthorized requests rejected

Frontend:
- provider list renders
- add provider form calls API
- secret is cleared after save
- test result visible
- disable action updates UI

Step 6 — Run checks:
Backend:
python -m ruff check .
python -m pytest -q

Frontend:
npm run lint
npm test if present
npm run build

Deliverable summary:
- endpoints
- UI pages
- security guarantees
- whether runtime gateway reads DB provider config now or later
```

---

# M7B — Provider health and fallback visibility prompt

```text
Implement M7B: Provider health and fallback visibility.

Goal:
Give the BO enough provider observability to understand whether fallback is happening because of provider errors/configuration.

Scope:
Small observability additions only.
Do not implement complex circuit breakers yet.

Backend:
Add provider health summary endpoint:
GET /admin/providers/health

Return:
- configured providers
- active/inactive
- last_test_status
- recent request count per provider
- recent failure count per provider
- fallback_used count
- last failure error_code/error_message sanitized

Use existing gateway_requests. Do not add heavy aggregation tables.

Frontend:
Providers page:
- provider cards
- active status
- last test result
- recent calls
- recent failures
- fallback count
- link to filtered requests page

Tests:
- health endpoint aggregates seeded GatewayRequest rows
- disabled provider still shown but inactive
- no secrets leak

Run:
python -m ruff check .
python -m pytest -q
frontend lint/build/tests
```

---

# M8 — Agentor minimal runtime stabilization prompt

```text
Implement/harden M8: Agentor minimal runtime.

Context:
Agentor is a minimal workflow runtime that calls Conexus.
M8 deliverables:
- AgentRun model
- GraphState
- NodeExecutor
- ConexusClient
- MCP/ToolClient abstraction
- HumanApprovalCheckpoint
- RunLog
- one hardcoded workflow executes
- writer node calls Conexus
- critic node calls Conexus
- human approval can stop before write

Goal:
Make Agentor internally consistent, resumable, and safe as a local runtime spike.

Scope:
- agentor package only unless Conexus client contract needs a tiny backend test
- do not add database persistence yet unless already planned
- do not add broad multi-agent framework features
- do not build marketplace/agent registry

Step 1 — Inspect existing Agentor:
Check:
- agentor/agentor_runtime/models.py
- agentor/agentor_runtime/executor.py
- agentor/agentor_runtime/clients/conexus.py
- agentor/agentor_runtime/clients/tool.py
- agentor/agentor_runtime/services/run_log.py
- agentor/tests/*

Step 2 — Implement resume semantics:
Current expected behavior:
- run() starts from first node
- workflow can pause at HumanApprovalCheckpoint
- after checkpoint.approve(), resume(run) should continue after the checkpoint node
- no previous nodes should repeat
- no duplicate NodeOutcome entries for completed nodes
- rejected checkpoint marks run rejected
- run.finished_at remains None while awaiting approval
- run.finished_at is set when terminal

Implementation options:
A. Add current_node_index/next_node_index to AgentRun
B. Derive next node from node_outcomes
Choose the smallest robust option.

Add:
NodeExecutor.resume(run)

Behavior:
- require run.status == AWAITING_APPROVAL
- require run.checkpoint is not None and decided
- if approved, continue remaining nodes
- if rejected, mark rejected and do not continue
- preserve state
- preserve earlier node outcomes
- set started_at only if missing
- set finished_at when completed/rejected/failed

Tests:
- pause at approval
- approve then resume runs remaining nodes only
- resume does not rerun previous LLM nodes
- reject then resume marks rejected
- resume without checkpoint raises clear error
- resume before decision raises clear error

Step 3 — Improve RunLog integration:
Either:
- make NodeExecutor optionally accept RunLogService
or
- keep RunLogService external but add helper to log run lifecycle

Smallest good design:
NodeExecutor(nodes, run_log: RunLogService | None = None)

Log:
- run.started
- node.completed
- node.failed
- checkpoint.awaiting_approval
- checkpoint.approved/rejected on resume
- run.finished

Tests:
- log entries appear in expected order
- failed node logs node.failed and run.finished with failed status
- checkpoint logs awaiting approval

Step 4 — ConexusClient hardening:
Enhance agentor ConexusClient:
- preserve Conexus request_id header if returned
- include provider/fallback_used if response returns them
- expose raw safely
- handle HTTP errors with status_code and parsed detail
- add optional request timeout override per call if easy
- do not log or expose API key

Tests:
- bearer auth sent
- response parses content/usage/model
- provider/fallback/request_id parsed if present
- malformed response raises ConexusClientError
- network error raises ConexusClientError
- HTTP error includes status code and detail

Step 5 — Tool abstraction:
Keep filesystem read-only by default.
Add:
- max file size guard
- binary file handling error
- path allowlist test
- path traversal test
- missing file returns ToolResult error

Do not add write tools yet.

Step 6 — Run checks:
From agentor:
python -m ruff check .
python -m pytest -q

Deliverable summary:
- resume behavior
- logging behavior
- Conexus client behavior
- remaining limitations
```

---

# M9 — Ontogony CMS workflow prompt

```text
Implement/harden M9: Ontogony CMS workflow.

Context:
M9 should produce CMS-ready Ontogony content through Agentor:
- Ontogony source reader tool
- Page planner node
- Writer node
- Critic node
- CMS formatter node
- Build/audit runner tool
- Draft/PR output
- no file written without approval

Goal:
Turn the current Ontogony CMS workflow from a demo into a safe local vertical slice that can produce draft content and stop before writing.

Scope:
- agentor workflow package
- read-only source tools
- safe approved write path only if approval is explicit
- no autonomous PR creation unless behind approval and tests

Do not:
- write to arbitrary filesystem paths
- create git commits automatically without approval
- run shell commands without explicit allowlist
- build a full CMS editor

Step 1 — Inspect current workflow:
Check:
- agentor/agentor_runtime/workflows/ontogony_cms.py
- tool client
- tests
- README usage
- Ontogony repo/content path assumptions if documented

Step 2 — Define workflow contract:
Inputs:
- topic: string
- source_paths: optional list[str]
- output_dir: optional path, must be under allowed root
- slug: optional string, generated if missing
- auto_approve: bool for tests only

Outputs in run.state:
- page_plan
- source_bundle
- draft
- critique
- cms_output
- proposed_output_path
- build_check_result if run
- approval checkpoint before write
- write_result only after approval

Step 3 — Safer frontmatter:
Replace f-string YAML frontmatter with yaml.safe_dump.

Fields:
- title
- description
- draft: true
- date if appropriate
- slug if appropriate
- tags if generated
- source: agentor

Tests:
- title with quotes/newlines does not break YAML
- description with colon does not break YAML
- frontmatter parses back as YAML

Step 4 — Source reader:
Improve source handling:
- use ToolClient read_file
- cap each source excerpt
- cap total source bundle
- include source path labels
- include error entries for missing/rejected files
- never read outside allowed roots when using FilesystemToolClient

Tests:
- source included
- source cap works
- missing source recorded as error but workflow continues
- path traversal rejected by filesystem tool

Step 5 — Planner/writer/critic:
Keep three Conexus calls:
1. Planner returns JSON
2. Writer returns markdown
3. Critic returns JSON score/notes

Hardening:
- JSON parse fallback for planner/critic
- validate plan shape
- validate critique score 0-10 when possible
- if critique score below threshold, keep draft but mark needs_revision=true
- do not auto-rewrite yet unless explicitly requested

Tests:
- happy path
- planner malformed JSON fallback
- critic malformed JSON fallback
- low critique score marks needs_revision
- workflow pauses before write

Step 6 — Approval + write behavior:
Current approval node should pause before write.
Add explicit post-approval write node or resume behavior:
- approval checkpoint proposes output path and preview
- after approval, write file only under allowed output root
- if rejected, no file written
- if auto_approve true in tests, write may proceed only if output root is configured
- if no output_dir, workflow completes with cms_output but no file write

Recommended node sequence:
1. plan_page
2. gather_sources
3. write_draft
4. critique_draft
5. format_cms
6. approval
7. write_draft_file
8. build_check optional

Tests:
- without approval, no write
- with rejection, no write
- with approval and allowed output_dir, file written
- output path cannot escape allowed root
- duplicate resume does not write twice or handles existing file safely

Step 7 — Build/audit runner tool:
Implement minimal read-safe command runner only if local tool design already supports it.
If implementing:
- command allowlist only
- cwd must be under allowed root
- timeout
- capture stdout/stderr
- no shell=True
- do not run arbitrary user command

For Ontogony:
- optional build command configured by caller
- record build_check_result
- failure marks run failed or needs_manual_review depending design

Tests:
- allowed command runs
- disallowed command rejected
- timeout handled
- build failure captured

Step 8 — README:
Update Agentor README:
- how to run workflow
- safe filesystem roots
- approval/resume flow
- no-file-write-until-approval guarantee
- limitations

Step 9 — Run checks:
From agentor:
python -m ruff check .
python -m pytest -q

Deliverable summary:
- workflow contract
- safety guarantees
- approval/write behavior
- tests
- remaining limitations
```

---

# M10 — MCP/tool layer prompt

```text
Implement M10: MCP/tool layer foundation.

Context:
M10 introduces a tool layer for Agentor/Conexus-adjacent workflows:
- MCP server for repo/filesystem tools
- later .NET MCP server for database/schema tools
- permissions and audit logs
- tool result schemas
- read-only tools first
- write/destructive tools require approval
- all tool calls are logged

Goal:
Create a minimal, safe, testable tool layer. Start read-only. Do not build a broad agent marketplace.

Scope:
- Agentor tool abstraction
- MCP-compatible or MCP-inspired interface if dependency is not ready
- filesystem/repo read tools
- audit logging
- permission policy
- tests

Do not:
- add destructive tools without approval gate
- run arbitrary shell commands
- expose entire filesystem
- add database mutation tools
- build A2A or multi-agent consensus

Step 1 — Inspect current ToolClient:
Check:
- agentor_runtime.clients.tool
- workflow source usage
- existing tests
- any MCP-related docs

Step 2 — Define tool result schema:
Create stable schema/dataclasses:
ToolCall:
- id
- tool_name
- args
- run_id optional
- node_id optional
- requested_at

ToolResult:
- call_id
- tool_name
- ok
- content
- structured_content optional
- metadata
- error
- started_at
- finished_at
- duration_ms

ToolPermission:
- tool_name
- mode: read|write|destructive
- allowed_roots optional
- requires_approval bool

Step 3 — Tool audit log:
Implement in-memory ToolAuditLog first:
- append every tool call
- include allowed/denied
- include error
- include duration
- never include full secret values
- avoid logging huge file contents

Tests:
- successful read logged
- denied path logged
- unknown tool logged
- error logged

Step 4 — Permission policy:
Create ToolPermissionPolicy:
- allowed tool names
- read tools allowed by default only if configured
- write/destructive require approval token/checkpoint
- filesystem paths must be under allowed roots
- max file size configurable

Tests:
- allowed read succeeds
- outside-root read denied
- write denied without approval
- unknown tool denied

Step 5 — Read-only repo/filesystem tools:
Implement tools:
- read_file
- list_dir
- stat_path
- search_text simple grep-like, bounded
- maybe read_many_files with count/size limit

Safety:
- no symlink escape
- no binary dump
- max file size
- max total search results
- no hidden secret file patterns if easy:
  - .env
  - id_rsa
  - *.pem
  - secrets.*
Return a clear error if blocked.

Tests:
- read allowed file
- block .env
- block large file
- search result cap
- symlink escape blocked

Step 6 — MCP boundary:
If an MCP Python dependency is already present or trivial, expose these tools through MCP.
If not, create an internal MCP-like interface and document that real MCP adapter is postponed.

Do not add heavy external dependencies unless justified.

Step 7 — Integrate with Ontogony workflow:
Use the permissioned/audited tool client for source reading.
Ensure all workflow tool calls are audited.

Tests:
- Ontogony workflow source reads appear in tool audit
- denied source does not crash workflow unless required

Step 8 — Run checks:
From agentor:
python -m ruff check .
python -m pytest -q

Deliverable summary:
- tool schemas
- permission policy
- audit log
- read tools
- MCP adapter status: implemented or intentionally postponed
- safety limitations
```

---

# M11 — Prompt/template registry prompt

This is not in the formal M5–M10 list, but it is a natural next milestone for your Conexus/Agentor direction.

```text
Implement M11: Prompt/template registry.

Goal:
Stop hardcoding workflow prompts inside Python functions and introduce a simple versioned prompt/template registry.

Scope:
- Agentor prompts first
- optional backend prompt registry only if small
- no complex prompt marketplace
- no eval automation yet

Requirements:
- prompts stored as markdown or YAML files
- each prompt has:
  - id
  - name
  - version
  - purpose
  - input variables
  - template body
  - model preference optional
- loader validates required variables
- renderer fills variables safely
- workflow nodes use registry instead of inline giant strings

Suggested structure:
agentor/prompts/
  ontogony/
    planner.v1.md
    writer.v1.md
    critic.v1.md

Implement:
- PromptTemplate dataclass
- PromptRegistry
- render_prompt(template_id, variables)
- missing variable error
- tests

Refactor Ontogony workflow:
- planner node uses planner.v1
- writer node uses writer.v1
- critic node uses critic.v1
- keep behavior equivalent

Tests:
- prompt loads
- variables render
- missing variable raises
- workflow still passes

Run:
python -m ruff check .
python -m pytest -q
```

---

# M12 — Evaluation harness prompt

```text
Implement M12: Lightweight eval harness for Conexus/Agentor outputs.

Goal:
Create a small eval harness so Ontogony workflow quality can be checked repeatedly without manually inspecting every generated draft.

Scope:
- local tests/evals
- no external eval platform
- no automated model training
- no complex scoring infrastructure

Implement:
EvalCase:
- id
- topic
- source_paths optional
- expected_properties
- forbidden_patterns
- min_critic_score optional

EvalResult:
- case_id
- passed
- score
- notes
- output_path optional
- run_id

Harness:
- load eval cases from YAML/JSON
- run Ontogony workflow with mocked or real Conexus depending flag
- evaluate:
  - cms_output exists
  - frontmatter parses
  - title exists
  - no forbidden patterns
  - critic score threshold if available
- write JSON report

Do not call real APIs by default.
Real API mode must require explicit env var:
AGENTOR_EVAL_REAL_LLM=true

Tests:
- mocked eval case passes
- forbidden pattern fails
- malformed frontmatter fails
- report written

Run:
python -m ruff check .
python -m pytest -q
```

---

# Best sequence from here

Use this order:

```text
1. M5 hardening
2. M6 BO request visibility
3. M6B request visibility polish
4. M7 provider management
5. M7B provider health/fallback visibility
6. M8 Agentor runtime stabilization
7. M9 Ontogony CMS workflow
8. M10 MCP/tool layer
9. M11 prompt/template registry
10. M12 eval harness
```

The important strategic rule: **finish Conexus observability before deepening Agentor**. M6/M7 make the gateway debuggable; M8/M9/M10 then become much easier to reason about.
