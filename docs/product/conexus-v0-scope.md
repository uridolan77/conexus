# Conexus v0 Scope

**Document path:** `/docs/product/conexus-v0-scope.md`  
**Status:** Draft v0.1  
**Owner:** Product / Architecture  
**Project:** Conexus  
**Last updated:** 2026-05-06

---

## 1. Executive Summary

Conexus v0 is a minimal, production-oriented **LLM gateway, prompt registry, and trace layer**.

Its purpose is to provide a stable internal platform through which applications can send LLM requests, route them through configured providers, manage reusable prompts, and observe usage, latency, cost, and errors.

Conexus v0 is not an agent framework, not a full workflow engine, not a RAG platform, not a fine-tuning system, and not a general AI operating system. Those capabilities may be added later, but v0 must establish a clean, testable, maintainable foundation first.

The central goal of v0 is to prove one reliable vertical slice:

```text
Client application
  -> Conexus API
  -> Request validation
  -> Prompt/template resolution
  -> Model routing
  -> Provider adapter
  -> LLM provider
  -> Response normalization
  -> Trace/usage logging
  -> Admin visibility
```

If this slice is clean, the later Conexus vision can grow safely. If this slice becomes messy, every later feature will amplify the mess.

---

## 2. Product Definition

### 2.1 What Conexus Is

Conexus is an internal AI infrastructure layer that decouples business applications from direct LLM-provider integration.

Instead of every application calling OpenAI, Anthropic, Gemini, local models, or future providers directly, applications call Conexus. Conexus becomes the controlled point for:

- provider abstraction
- prompt versioning
- model routing
- usage tracing
- cost tracking
- error handling
- policy enforcement
- later evaluation and optimization

### 2.2 What Conexus v0 Is

Conexus v0 is the smallest useful version of this platform.

It should support:

1. Submitting a basic LLM request through a stable API.
2. Routing that request to a configured provider/model.
3. Resolving a registered prompt/template when requested.
4. Receiving a normalized response.
5. Logging the full request lifecycle as a trace.
6. Viewing basic usage and trace data in an admin interface.
7. Running tests that prove the request lifecycle works.

### 2.3 What Conexus v0 Is Not

Conexus v0 is explicitly **not**:

- a multi-agent system
- a LangGraph replacement
- an MCP server/client hub
- a DSPy optimization platform
- a CL-PEFT training system
- a RAG platform
- a vector database manager
- a workflow automation system
- a complex rules engine
- a no-code AI builder
- a full enterprise admin suite
- a billing platform
- a public SaaS product

These may become later modules, but none are part of v0 unless explicitly approved by architecture review.

---

## 3. Core Product Goals

### Goal 1 — Provide a Stable LLM Request Gateway

Applications should be able to send requests to Conexus without knowing the details of the underlying provider.

The calling application should not need to know:

- provider SDK details
- provider-specific message formats
- provider-specific response formats
- provider-specific error formats
- provider-specific token/cost reporting formats

Conexus should normalize these concerns.

### Goal 2 — Create a Provider Abstraction

Conexus must define a clean provider adapter contract.

Each provider implementation should be isolated behind this contract. The rest of the system should interact with providers through internal interfaces, not provider SDKs directly.

v0 should implement at least one provider adapter, preferably OpenAI first.

### Goal 3 — Establish Prompt Registry Foundations

Conexus should support reusable prompts/templates with version metadata.

The v0 prompt registry does not need advanced collaboration, branching, approval workflows, or automatic evaluation. It only needs enough structure to avoid hardcoded prompts scattered across client applications.

### Goal 4 — Capture Request Traces

Every LLM request should produce a trace record.

The trace should make it possible to answer:

- who or what called Conexus?
- which prompt/template was used?
- which model/provider handled the request?
- how long did it take?
- did it succeed or fail?
- how many tokens were used, if available?
- what was the estimated cost, if available?
- what error occurred, if any?

### Goal 5 — Provide Basic Admin Visibility

v0 should include a simple admin UI or dashboard showing:

- recent requests
- provider/model used
- latency
- status
- error summary
- token usage when available
- cost estimate when available
- prompt/template used when available

The admin UI does not need to be beautiful in v0, but it must be functional and useful.

### Goal 6 — Keep the Architecture Small and Extensible

The v0 implementation should create stable seams for future functionality without prematurely implementing everything.

The architecture should make it easy to later add:

- more providers
- routing policies
- evaluation runs
- caching
- fallback models
- streaming
- WebSocket support
- RAG integrations
- agent orchestration
- DSPy optimization
- MCP integration

But v0 should not implement those unless required for the core vertical slice.

---

## 4. Primary Users

### 4.1 Developer User

A developer uses Conexus to integrate LLM capabilities into an application without directly wiring every provider.

Needs:

- clear API
- predictable response format
- useful errors
- reliable local/dev configuration
- testable request lifecycle

### 4.2 Admin / Operator

An operator uses Conexus to inspect usage and troubleshoot failures.

Needs:

- request trace visibility
- error visibility
- latency visibility
- provider/model visibility
- prompt usage visibility

### 4.3 Product / Prompt Owner

A prompt owner manages reusable prompts used by applications.

Needs:

- prompt name
- prompt description
- prompt template
- version
- variables
- status metadata

In v0 this can be simple. Advanced workflow is deferred.

### 4.4 Future Agent System Consumer

Agentor or another agentic system may later use Conexus as its LLM execution layer.

In v0, Conexus should not depend on Agentor. The dependency direction must remain:

```text
Agentor -> Conexus
```

Never:

```text
Conexus -> Agentor
```

---

## 5. Core Use Cases

### Use Case 1 — Direct LLM Completion Request

A client application sends a direct request to Conexus containing messages, model preferences, and optional metadata.

Conexus validates the request, routes it to the selected provider/model, returns a normalized response, and records a trace.

### Use Case 2 — Prompt Template Request

A client application sends a request referencing a registered prompt template by key and version.

Conexus resolves the template, injects variables, sends the final prompt/messages to the provider, returns a normalized response, and records which template/version was used.

### Use Case 3 — Inspect Recent Traces

An admin opens the admin UI and sees recent LLM calls with status, latency, provider, model, token usage, and errors.

### Use Case 4 — Add or Update a Prompt Template

A product or developer user creates or updates a prompt template.

In v0 this can be done through a simple admin UI, seed file, database migration, or internal endpoint. The exact interface can be chosen based on implementation simplicity.

### Use Case 5 — Provider Health Check

An admin or developer checks whether Conexus and its configured provider are reachable.

The system exposes health endpoints for basic diagnostics.

---

## 6. v0 Functional Scope

### 6.1 LLM Request API

Conexus v0 must expose an API for submitting LLM requests.

Minimum capabilities:

- accept messages or prompt reference
- accept optional model/provider preference
- accept metadata from the caller
- validate required fields
- call provider adapter
- return normalized response
- log trace

Supported request modes:

1. **Direct messages mode**
2. **Prompt-template mode**

Streaming is out of scope for v0 unless it already exists and can be supported without architectural disruption.

### 6.2 Provider Adapter Layer

Conexus v0 must define an internal provider adapter interface.

Minimum adapter responsibilities:

- convert normalized Conexus request to provider-specific request
- execute provider call
- convert provider response to normalized Conexus response
- convert provider errors to normalized Conexus errors
- extract token usage when available
- expose provider/model identity

At least one provider must be implemented in v0.

Recommended first provider:

- OpenAI

Optional if already easy:

- Anthropic
- Gemini

Do not implement multiple providers unless the abstraction is already stable enough and the first provider is working.

### 6.3 Model Router

Conexus v0 must include a simple routing layer.

In v0, routing can be deterministic and configuration-based.

Minimum routing behavior:

- use explicit provider/model from request when allowed
- otherwise use configured default provider/model
- reject unknown provider/model combinations
- record chosen provider/model in trace

Out of scope for v0:

- dynamic cost optimization
- latency-aware routing
- fallback chains
- A/B routing
- prompt-based routing
- automatic provider benchmarking

The router should be simple now, but structured so these capabilities can be added later.

### 6.4 Prompt Registry

Conexus v0 must include a basic prompt registry.

Minimum prompt fields:

- id
- key
- name
- description
- template/body
- version
- variables/schema
- status
- created_at
- updated_at

Recommended statuses:

- draft
- active
- archived

Minimum prompt behavior:

- create prompt
- read prompt
- list prompts
- resolve prompt by key and version or active version
- render prompt with variables
- record prompt id/version in trace

Out of scope for v0:

- prompt approval workflows
- prompt branching
- prompt experiments
- prompt scoring
- prompt rollback UI
- collaborative editing
- rich prompt diffing

### 6.5 Trace / Usage Logging

Conexus v0 must record every request lifecycle.

Minimum trace fields:

- trace_id
- request_id or correlation_id
- caller/application identifier
- provider
- model
- prompt_id if used
- prompt_version if used
- status
- start_time
- end_time
- latency_ms
- input token count if available
- output token count if available
- total token count if available
- estimated cost if available
- error code if failed
- error message summary if failed
- created_at

Sensitive data handling must be deliberate. See section 13.

### 6.6 Admin UI

Conexus v0 must include basic admin visibility.

Minimum pages or panels:

1. **Dashboard Overview**
   - request count
   - success/failure count
   - average latency
   - recent errors

2. **Trace List**
   - timestamp
   - caller
   - provider
   - model
   - prompt key/version
   - status
   - latency
   - tokens/cost if available

3. **Trace Detail**
   - request metadata
   - provider/model
   - prompt/template reference
   - normalized error if failed
   - token/cost info

4. **Prompt Registry List**
   - prompt key
   - name
   - version
   - status
   - updated date

5. **Prompt Detail**
   - template/body
   - variables
   - version metadata

The admin UI does not need advanced design in v0. It does need clean structure and enough information to debug.

### 6.7 Configuration

Conexus v0 must support configuration for:

- default provider
- default model
- provider API keys
- allowed providers/models
- logging behavior
- trace retention defaults if applicable
- environment-specific settings

Secrets must not be hardcoded.

### 6.8 Health Checks

Conexus v0 must expose basic health endpoints.

Recommended endpoints:

- service health
- database health if applicable
- provider configuration health

Provider health should not necessarily make a paid LLM call unless explicitly configured.

---

## 7. Out of Scope for v0

The following are explicitly out of scope unless separately approved:

### 7.1 Agentic Framework Features

- autonomous planning
- tool execution
- multi-agent coordination
- agent memory
- agent role registry
- agent workflow graph
- LangGraph-like orchestration

These belong to Agentor or a later Conexus module.

### 7.2 Advanced RAG

- vector ingestion
- chunking pipelines
- embedding management
- retrieval ranking
- hybrid search
- source citation pipelines

RAG may use Conexus later, but Conexus v0 does not build RAG.

### 7.3 Prompt Optimization

- DSPy optimization
- automatic prompt improvement
- eval-driven prompt mutation
- prompt tournamenting
- model comparison dashboards

### 7.4 Fine-Tuning / CL-PEFT

- training jobs
- adapters
- LoRA/PEFT management
- dataset preparation
- training evaluation

### 7.5 Complex Routing

- automatic provider fallback
- budget-aware routing
- latency-aware routing
- quality-aware routing
- business-rule routing DSL

### 7.6 Enterprise Governance

- full RBAC
- organization hierarchy
- audit approval workflows
- enterprise billing
- tenant isolation
- compliance dashboards

Basic authentication/authorization may be required depending on deployment context, but enterprise governance is not v0.

---

## 8. Conceptual Architecture

### 8.1 High-Level Components

```text
Client Applications
        |
        v
Conexus API Layer
        |
        v
Request Validator
        |
        +-------------------+
        |                   |
        v                   v
Prompt Registry        Direct Messages
        |                   |
        +---------+---------+
                  |
                  v
            Model Router
                  |
                  v
          Provider Adapter
                  |
                  v
            LLM Provider
                  |
                  v
       Response Normalizer
                  |
                  v
          Trace Logger
                  |
                  v
             Admin UI
```

### 8.2 Component Responsibilities

#### API Layer

Receives external requests and returns normalized responses.

Responsibilities:

- authentication hook if needed
- request parsing
- input validation
- response shaping
- error mapping

#### Request Validator

Ensures the request is structurally valid before execution.

Responsibilities:

- validate required fields
- validate mode: direct or prompt-template
- validate provider/model references
- validate prompt variables where possible

#### Prompt Registry

Stores and resolves reusable prompt templates.

Responsibilities:

- manage prompt records
- resolve active version
- render template with variables
- expose prompt metadata

#### Model Router

Selects the provider/model to use.

Responsibilities:

- apply default provider/model
- validate allowed provider/model
- return route decision
- record route reason if useful

#### Provider Adapter

Isolates provider-specific integration.

Responsibilities:

- translate request
- call provider
- normalize response
- normalize errors
- extract token/cost metadata

#### Response Normalizer

Ensures client applications receive a stable response format regardless of provider.

Responsibilities:

- normalize generated text/content
- normalize usage metadata
- normalize finish reason
- normalize provider-specific identifiers

#### Trace Logger

Records execution lifecycle.

Responsibilities:

- create trace start record
- update trace after success/failure
- store latency, provider, model, tokens, cost, errors

#### Admin UI

Displays operational visibility.

Responsibilities:

- dashboard summary
- trace list
- trace detail
- prompt list
- prompt detail

---

## 9. Core Domain Entities

### 9.1 LlmRequest

Represents a normalized request submitted to Conexus.

Suggested fields:

```text
LlmRequest
- request_id
- caller_id
- mode
- messages
- prompt_key
- prompt_version
- variables
- provider_preference
- model_preference
- temperature
- max_tokens
- metadata
```

Notes:

- `messages` are used for direct mode.
- `prompt_key`, `prompt_version`, and `variables` are used for prompt-template mode.
- The system should reject requests that mix incompatible modes.

### 9.2 LlmResponse

Represents a normalized response returned by Conexus.

Suggested fields:

```text
LlmResponse
- request_id
- trace_id
- provider
- model
- content
- finish_reason
- usage
- metadata
```

### 9.3 Provider

Represents an LLM provider integration.

Suggested fields:

```text
Provider
- provider_id
- key
- name
- enabled
- supported_models
- configuration_reference
```

### 9.4 ModelDefinition

Represents a configured model.

Suggested fields:

```text
ModelDefinition
- model_id
- provider_key
- model_name
- display_name
- enabled
- context_window
- supports_streaming
- supports_tools
- input_cost_per_token
- output_cost_per_token
```

For v0, this can be config-based rather than database-managed.

### 9.5 PromptTemplate

Represents a reusable prompt.

Suggested fields:

```text
PromptTemplate
- prompt_id
- key
- name
- description
- version
- status
- template
- variables_schema
- created_at
- updated_at
```

### 9.6 Trace

Represents a recorded request lifecycle.

Suggested fields:

```text
Trace
- trace_id
- request_id
- caller_id
- mode
- prompt_id
- prompt_key
- prompt_version
- provider
- model
- status
- start_time
- end_time
- latency_ms
- input_tokens
- output_tokens
- total_tokens
- estimated_cost
- error_code
- error_message_summary
- metadata
- created_at
```

### 9.7 Usage

Represents token/cost usage.

Suggested fields:

```text
Usage
- input_tokens
- output_tokens
- total_tokens
- estimated_cost
- currency
```

Usage may be embedded in trace and response for v0.

---

## 10. API Scope

The exact API shape may vary by backend stack, but v0 should expose stable conceptual endpoints.

### 10.1 Submit LLM Request

```http
POST /api/llm/requests
```

Purpose:

Submit a direct or prompt-template LLM request.

Direct request example:

```json
{
  "mode": "direct",
  "callerId": "conexus-bo",
  "messages": [
    {
      "role": "system",
      "content": "You are a precise editorial assistant."
    },
    {
      "role": "user",
      "content": "Improve this paragraph."
    }
  ],
  "model": {
    "provider": "openai",
    "name": "gpt-5.5"
  },
  "options": {
    "temperature": 0.3,
    "maxTokens": 1000
  },
  "metadata": {
    "feature": "chapter-editor"
  }
}
```

Prompt-template request example:

```json
{
  "mode": "prompt_template",
  "callerId": "conexus-bo",
  "prompt": {
    "key": "chapter_critique",
    "version": "active"
  },
  "variables": {
    "chapterTitle": "The Immanentist Underground",
    "chapterText": "..."
  },
  "model": {
    "provider": "openai",
    "name": "gpt-5.5"
  },
  "metadata": {
    "feature": "critique"
  }
}
```

Response example:

```json
{
  "requestId": "req_123",
  "traceId": "trace_456",
  "provider": "openai",
  "model": "gpt-5.5",
  "content": "...",
  "finishReason": "stop",
  "usage": {
    "inputTokens": 1200,
    "outputTokens": 450,
    "totalTokens": 1650,
    "estimatedCost": 0.0,
    "currency": "USD"
  },
  "metadata": {}
}
```

### 10.2 List Prompts

```http
GET /api/prompts
```

Purpose:

List registered prompts.

Minimum filters:

- status
- key

### 10.3 Get Prompt

```http
GET /api/prompts/{promptId}
```

Purpose:

Retrieve one prompt template and metadata.

### 10.4 Create Prompt

```http
POST /api/prompts
```

Purpose:

Create a prompt template.

Minimum body:

```json
{
  "key": "chapter_critique",
  "name": "Chapter Critique",
  "description": "Critiques a philosophical chapter.",
  "version": "1.0.0",
  "status": "active",
  "template": "...",
  "variablesSchema": {
    "chapterTitle": "string",
    "chapterText": "string"
  }
}
```

### 10.5 List Traces

```http
GET /api/traces
```

Purpose:

List recent request traces.

Minimum filters:

- status
- provider
- model
- callerId
- promptKey
- date range

### 10.6 Get Trace

```http
GET /api/traces/{traceId}
```

Purpose:

View detailed trace metadata.

### 10.7 Health Check

```http
GET /api/health
```

Purpose:

Return service health.

Example response:

```json
{
  "status": "healthy",
  "service": "conexus",
  "version": "0.1.0",
  "checks": {
    "database": "healthy",
    "configuration": "healthy"
  }
}
```

---

## 11. Admin UI Scope

### 11.1 Dashboard Page

The dashboard should answer:

- Is Conexus working?
- How many requests are being processed?
- Are errors happening?
- Which models/providers are being used?
- Is latency acceptable?

Minimum widgets:

- total requests in selected period
- success count
- failure count
- average latency
- recent errors
- top providers/models

### 11.2 Trace List Page

Columns:

- timestamp
- status
- caller
- provider
- model
- prompt key/version
- latency
- total tokens
- estimated cost

Actions:

- open trace detail
- filter by status
- filter by provider/model
- filter by caller
- filter by prompt

### 11.3 Trace Detail Page

Sections:

- trace metadata
- request metadata
- prompt metadata if used
- provider/model route
- timing
- usage/cost
- error details if failed

Sensitive prompt/request content should be handled according to the data policy in section 13.

### 11.4 Prompt Registry Page

Columns:

- key
- name
- version
- status
- updated at

Actions:

- view prompt
- create prompt
- edit prompt if allowed in v0
- archive prompt if allowed in v0

### 11.5 Prompt Detail Page

Sections:

- metadata
- template/body
- variables schema
- version
- status

---

## 12. Data Storage Scope

v0 may use a relational database, document database, or existing project persistence layer. The specific technology should follow the repo’s established stack.

Minimum persisted data:

- prompt templates
- traces
- provider/model configuration if not config-file based

Recommended principle:

> Store operational metadata by default. Store raw prompt/request/response content only if explicitly needed and governed by policy.

---

## 13. Security, Privacy, and Data Handling

### 13.1 Secrets

Provider API keys must be stored securely using environment variables, secret manager, or deployment-specific secure configuration.

Forbidden:

- hardcoded API keys
- keys in source control
- keys in frontend code
- keys in prompt records
- keys in trace records

### 13.2 Request Content Logging

Conexus must decide whether to store raw prompt/request/response content.

Default v0 recommendation:

- store metadata by default
- optionally store redacted request/response snippets for debugging
- avoid full raw body logging unless explicitly enabled

### 13.3 Sensitive Data

LLM requests may contain sensitive business, user, or personal data.

v0 should include a clear configuration flag for content logging.

Suggested config:

```text
TraceContentLogging = none | metadata_only | redacted | full
```

Recommended default:

```text
metadata_only
```

### 13.4 Authentication and Authorization

If Conexus is deployed beyond local development, API access should be protected.

Minimum requirement for v0 production-like deployment:

- API key, bearer token, or existing internal auth mechanism for client applications
- admin UI protected from public access

Full RBAC is out of scope for v0.

### 13.5 Error Exposure

Client responses should not expose raw provider errors that may contain sensitive internal details.

Conexus should normalize errors into safe external messages while preserving detailed diagnostics in internal traces.

---

## 14. Observability Requirements

v0 must provide enough observability to troubleshoot the request lifecycle.

Minimum logging:

- request received
- provider/model selected
- provider call started
- provider call succeeded/failed
- trace persisted

Minimum metrics or dashboard-level aggregates:

- request count
- success/failure count
- latency
- provider/model usage
- token usage if available
- error count by type

Tracing should include correlation IDs where possible.

---

## 15. Error Handling Requirements

Conexus v0 must normalize common error classes.

Recommended error categories:

```text
ValidationError
AuthenticationError
AuthorizationError
ProviderConfigurationError
ProviderRateLimitError
ProviderTimeoutError
ProviderUnavailableError
ProviderResponseError
PromptNotFoundError
PromptRenderError
UnknownExecutionError
```

Each error response should include:

- stable error code
- safe message
- trace id if available

Example:

```json
{
  "error": {
    "code": "PROVIDER_TIMEOUT",
    "message": "The selected model provider did not respond in time.",
    "traceId": "trace_456"
  }
}
```

---

## 16. Testing Requirements

v0 is not accepted without tests for the main request lifecycle.

### 16.1 Required Test Categories

#### Unit Tests

- prompt rendering
- request validation
- provider adapter normalization
- route selection
- error normalization
- cost/token calculation if implemented

#### Integration Tests

- direct request lifecycle using mocked provider
- prompt-template request lifecycle using mocked provider
- failed provider request creates failed trace
- successful provider request creates successful trace

#### API Tests

- submit direct request
- submit prompt-template request
- list prompts
- list traces
- get trace detail
- health check

### 16.2 Provider Testing

Real provider calls should not be required for normal automated tests.

Use provider mocks/fakes for CI and local deterministic tests.

Optional manual smoke test:

- one real provider call with test API key

### 16.3 Acceptance Test

The key v0 acceptance test:

```text
Given a valid prompt-template request,
when the client submits it to Conexus,
then Conexus resolves the prompt,
routes to the configured provider,
receives a response,
returns a normalized response,
and records a trace visible in the admin UI.
```

---

## 17. Performance Requirements

v0 does not need advanced performance optimization.

However, it should avoid obvious problems.

Minimum expectations:

- Conexus overhead should be small compared to provider latency.
- Trace logging should not block response longer than necessary.
- Admin trace list should paginate.
- Large request/response bodies should not be loaded unnecessarily in list views.

Out of scope:

- high-throughput queueing
- distributed tracing
- horizontal scale testing
- advanced caching
- streaming optimization

---

## 18. Configuration Requirements

Recommended configuration sections:

```text
Conexus
- Environment
- DefaultProvider
- DefaultModel
- ContentLoggingMode
- TraceRetentionDays

Providers
- OpenAI
  - Enabled
  - ApiKey
  - DefaultModel
  - AllowedModels

Database
- ConnectionString

Admin
- Enabled
- AuthMode
```

No provider secrets may appear in committed configuration files.

---

## 19. Deployment Assumptions

v0 deployment should be simple.

Expected environments:

- local development
- staging/dev server
- later production-like deployment

Minimum deployment needs:

- backend service
- database if required
- frontend/admin UI if separate
- environment variables/secrets
- provider API key

Do not introduce complex deployment infrastructure unless the repo already uses it.

---

## 20. Development Methodology

Conexus should be developed using **SDD + SPDD + bounded agentic execution**.

### 20.1 SDD Role

This document and related specs define what must be true.

Relevant specs should live under:

```text
/docs/product
/docs/architecture
/docs/specs
```

### 20.2 SPDD Role

Every significant feature/refactor should have a REASONS Canvas under:

```text
/docs/ai/reasons-canvases
```

or:

```text
/ai/reasons-canvases
```

depending on final repo convention.

Each Canvas must include:

```text
R — Requirements
E — Entities
A — Approach
S — Structure
O — Operations
N — Norms
S — Safeguards
```

### 20.3 Agentic Execution Role

AI agents may inspect, plan, edit, test, and summarize, but only within the boundaries of the spec and Canvas.

Agents must not:

- invent new architecture
- add unrelated features
- perform broad refactors without approval
- silently ignore test failures
- change provider contracts without updating specs
- add new dependencies without justification

---

## 21. Recommended Repo Structure

Suggested documentation structure:

```text
/docs
  /product
    conexus-v0-scope.md
    roadmap.md
  /architecture
    system-overview.md
    bounded-contexts.md
    non-negotiables.md
  /specs
    llm-request-api.md
    provider-abstraction.md
    prompt-registry.md
    trace-logging.md
    admin-ui.md
  /adr
    0001-provider-abstraction.md
    0002-trace-content-logging.md
    0003-prompt-registry-storage.md
  /ai
    /reasons-canvases
    /implementation-prompts
    /review-prompts
```

Suggested backend structure, adjusted to actual stack:

```text
/src
  /api
  /application
    /llm
    /prompts
    /traces
  /domain
    /providers
    /prompts
    /traces
  /infrastructure
    /providers
      /openai
    /persistence
    /configuration
  /admin
/tests
```

Do not force this structure if the current repo already has a coherent architecture. Use it as a reference pattern.

---

## 22. v0 Acceptance Criteria

Conexus v0 is accepted when all of the following are true:

### Core Gateway

- A client can submit a direct LLM request.
- A client can submit a prompt-template LLM request.
- Requests are validated before execution.
- Responses are normalized.
- Errors are normalized.

### Provider Abstraction

- At least one provider adapter is implemented.
- Provider-specific SDK usage is isolated inside adapter code.
- The rest of the system depends on internal provider interfaces.

### Routing

- Default provider/model routing works.
- Explicit allowed provider/model selection works.
- Unknown provider/model selection is rejected safely.

### Prompt Registry

- Prompt templates can be listed.
- A prompt can be retrieved by key/version or active version.
- A prompt can be rendered with variables.
- Prompt usage is recorded in traces.

### Tracing

- Successful requests create successful traces.
- Failed requests create failed traces.
- Trace records include provider, model, latency, status, and error summary if applicable.
- Token/cost data is recorded when available.

### Admin UI

- Admin user can see recent traces.
- Admin user can open trace detail.
- Admin user can see prompt list.
- Admin user can open prompt detail.

### Testing

- Unit tests cover prompt rendering, routing, provider normalization, and validation.
- Integration tests cover successful and failed request lifecycle with mocked provider.
- API tests cover main endpoints.
- Test suite runs without real provider calls.

### Documentation

- v0 scope document exists.
- provider abstraction spec exists.
- prompt registry spec exists.
- trace logging spec exists.
- at least one REASONS Canvas exists for the first implementation slice.

---

## 23. Recommended First Implementation Slice

The first implementation slice should be:

```text
Provider abstraction + direct request lifecycle + trace logging
```

Do not start with admin UI, agents, DSPy, MCP, caching, or advanced prompt tooling.

### Slice 1 Scope

Build:

- normalized LLM request type
- normalized LLM response type
- provider adapter interface
- OpenAI provider adapter
- simple router
- direct request endpoint
- trace persistence
- tests using mocked provider

Acceptance:

```text
A direct request can be submitted, routed, executed through the provider adapter, normalized, returned, and traced.
```

### Slice 2 Scope

Build:

- prompt template entity
- prompt storage
- prompt resolver
- prompt rendering
- prompt-template request mode
- prompt usage in traces

Acceptance:

```text
A prompt-template request can be submitted, resolved, executed, returned, and traced with prompt metadata.
```

### Slice 3 Scope

Build:

- trace list API
- trace detail API
- simple admin trace UI

Acceptance:

```text
An admin can view recent request traces and open trace details.
```

### Slice 4 Scope

Build:

- prompt list API/UI
- prompt detail API/UI
- simple prompt creation/editing if needed

Acceptance:

```text
An admin or developer can inspect registered prompts and their versions.
```

---

## 24. Risks

### Risk 1 — Scope Explosion

Conexus can easily become a catch-all AI platform before the gateway foundation is stable.

Mitigation:

- enforce v0 non-goals
- require architecture review for new modules
- use REASONS Canvas for every major change

### Risk 2 — Provider Leakage

Provider-specific assumptions may leak into the rest of the system.

Mitigation:

- strict provider adapter boundary
- normalized request/response types
- tests proving provider isolation

### Risk 3 — Trace Data Privacy

Traces may accidentally store sensitive prompt or response content.

Mitigation:

- metadata-only default
- explicit content logging mode
- redaction strategy before full logging

### Risk 4 — Prompt Registry Overdesign

Prompt management can become too complex too early.

Mitigation:

- support key/version/status only in v0
- defer approvals, experiments, scoring, and branching

### Risk 5 — Admin UI Distraction

The admin UI can consume too much effort before the backend contract is stable.

Mitigation:

- implement simple functional UI only
- prioritize trace visibility over design polish

### Risk 6 — Agentic Overreach

AI coding agents may introduce broad refactors, dependencies, or architecture changes.

Mitigation:

- every implementation prompt must reference this scope document
- require impacted-files preview before editing
- require tests and summary after editing

---

## 25. Decision Log Required Before Implementation

Before v0 implementation, create or confirm ADRs for:

1. Provider abstraction boundary.
2. Trace content logging policy.
3. Prompt registry storage approach.
4. Backend/API framework conventions.
5. Admin UI placement: same app or separate frontend.
6. Authentication approach for API/admin access.

---

## 26. Definition of Done

A Conexus v0 feature is done only when:

- it matches this scope or an approved spec
- tests are added or updated
- relevant docs/specs are updated
- no unrelated refactors were introduced
- provider-specific logic remains isolated
- errors are normalized
- traces are created where applicable
- the implementation can be explained in a short review note

Conexus v0 as a whole is done only when:

```text
A client can submit a request,
Conexus can route it to a provider,
the provider response is normalized,
the lifecycle is traced,
and an admin can inspect what happened.
```

---

## 27. Final v0 Boundary Statement

Conexus v0 should be boring, stable, and useful.

It is not the full AI platform yet.

It is the foundation that makes the full AI platform possible.

The correct v0 success condition is not impressive complexity. The correct success condition is:

```text
One clean, observable, testable LLM execution path.
```

Everything else comes after that.

