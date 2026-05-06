# Provider Abstraction Specification

**Document path:** `/docs/specs/provider-abstraction.md`  
**Status:** Draft v0.1  
**Project:** Conexus  
**Related scope:** `/docs/product/conexus-v0-scope.md`  
**Last updated:** 2026-05-06

---

## 1. Purpose

The provider abstraction defines the boundary between Conexus and external LLM providers.

Its job is to ensure that the rest of Conexus does not depend directly on provider SDKs, provider-specific request formats, provider-specific response formats, or provider-specific error semantics.

Conexus should expose one stable internal execution contract:

```text
Normalized Conexus request
  -> Provider adapter contract
  -> Provider-specific SDK/API
  -> Normalized Conexus response
```

The first implementation target is a clean provider adapter for OpenAI, but the abstraction must be shaped so later providers such as Anthropic, Gemini, Azure OpenAI, local models, or internal model gateways can be added without rewriting the gateway core.

---

## 2. Core Principle

Provider-specific logic must be isolated.

The rest of the Conexus system should know only about:

- normalized request objects
- normalized response objects
- normalized usage objects
- normalized error objects
- provider/model identifiers
- provider capabilities

The rest of the system should not know about:

- provider SDK classes
- provider-specific message schemas
- provider-specific token response formats
- provider-specific finish reasons
- provider-specific exception types
- provider-specific rate-limit payloads
- provider-specific API paths

This boundary is non-negotiable for v0.

---

## 3. Scope

### 3.1 In Scope for v0

The provider abstraction v0 includes:

1. A provider adapter interface.
2. Normalized request type.
3. Normalized response type.
4. Normalized usage type.
5. Normalized error type.
6. Provider capability metadata.
7. Provider/model identity model.
8. Request-to-provider translation.
9. Provider-to-response translation.
10. Provider error normalization.
11. Basic timeout and cancellation support.
12. Tests using fake/mock providers.
13. One concrete OpenAI adapter.

### 3.2 Out of Scope for v0

The provider abstraction v0 does not include:

- streaming responses
- tool/function calling
- structured output enforcement
- multimodal input/output
- audio models
- image generation
- provider fallback chains
- latency-aware routing
- cost-aware routing
- automatic benchmarking
- dynamic model selection by quality
- provider-side prompt caching optimization
- provider-specific fine-tuning APIs
- provider-specific batch APIs

These can be added after the basic execution path is stable.

---

## 4. Design Goals

### Goal 1 — Stable Internal Contract

All Conexus components should call providers through a stable internal interface.

When a provider SDK changes, the impact should be limited to the provider adapter implementation.

### Goal 2 — Provider Isolation

Provider-specific details should not leak into:

- API controllers
- request validation
- prompt registry
- model router
- trace logger
- admin UI
- application services
- domain models

### Goal 3 — Testability

The gateway core should be testable without making real provider calls.

The provider abstraction should support fake/mock providers for deterministic unit and integration tests.

### Goal 4 — Extensibility Without Overengineering

The abstraction should make future providers possible, but v0 should not implement a complex plugin framework.

Prefer a small, explicit adapter contract over a large speculative abstraction.

### Goal 5 — Trace-Friendly Execution

The adapter should return enough metadata for Conexus to record useful traces:

- provider
- model
- provider request id if available
- token usage if available
- finish reason
- normalized status
- normalized error if failed

---

## 5. Architectural Boundary

### 5.1 Allowed Dependency Direction

The dependency direction must be:

```text
Conexus gateway/application layer
  -> provider abstraction interface
  -> provider adapter implementation
  -> provider SDK/API
```

Forbidden direction:

```text
API/controller/admin layer
  -> OpenAI SDK directly
```

Forbidden direction:

```text
Prompt registry
  -> provider SDK directly
```

Forbidden direction:

```text
Trace logger
  -> provider SDK directly
```

### 5.2 Recommended Layering

Suggested conceptual layering:

```text
/src
  /application
    /llm
      LlmExecutionService
      LlmRequestValidator
      ModelRouter

  /domain
    /providers
      ProviderAdapter
      ProviderRequest
      ProviderResponse
      ProviderError
      ProviderUsage
      ProviderCapabilities

  /infrastructure
    /providers
      /openai
        OpenAiProviderAdapter
        OpenAiRequestMapper
        OpenAiResponseMapper
        OpenAiErrorMapper
```

Adapt this to the existing repo conventions. Do not force this exact structure if the repo already has a coherent layout.

---

## 6. Provider Adapter Contract

### 6.1 Conceptual Interface

The provider adapter should expose one main execution method.

Language-neutral shape:

```text
ProviderAdapter
- providerKey: string
- getCapabilities(): ProviderCapabilities
- supportsModel(modelName): boolean
- execute(request: ProviderRequest): ProviderResponse
```

Async-capable shape:

```text
ProviderAdapter
- providerKey: string
- getCapabilities(): ProviderCapabilities
- supportsModel(modelName): boolean
- executeAsync(request: ProviderRequest, cancellationToken): ProviderResponse
```

For .NET-style implementation, this could become:

```csharp
public interface ILlmProviderAdapter
{
    string ProviderKey { get; }

    ProviderCapabilities GetCapabilities();

    bool SupportsModel(string modelName);

    Task<ProviderResponse> ExecuteAsync(
        ProviderRequest request,
        CancellationToken cancellationToken = default);
}
```

The exact language syntax can vary, but the conceptual contract should remain stable.

### 6.2 Adapter Responsibilities

A provider adapter must:

1. Validate provider-specific prerequisites.
2. Convert a normalized `ProviderRequest` into the provider-specific request.
3. Call the provider SDK/API.
4. Convert the provider response into a normalized `ProviderResponse`.
5. Convert provider errors into normalized provider errors.
6. Extract token usage when available.
7. Extract provider request id when available.
8. Preserve enough metadata for tracing.

### 6.3 Adapter Non-Responsibilities

A provider adapter must not:

- decide business-level routing policy
- resolve prompt templates
- know about admin UI concerns
- persist traces directly
- perform broad request validation that belongs to Conexus
- know about application-specific caller logic
- implement agent workflow behavior
- mutate the original request in unexpected ways

---

## 7. Normalized Provider Request

### 7.1 Purpose

`ProviderRequest` is the internal request object passed from Conexus to a provider adapter.

It should represent the minimum provider-independent information needed for a basic text/chat completion request.

### 7.2 Suggested Shape

```text
ProviderRequest
- requestId: string
- provider: string
- model: string
- messages: ProviderMessage[]
- options: ProviderRequestOptions
- metadata: map<string, string | number | boolean>
```

### 7.3 ProviderMessage

```text
ProviderMessage
- role: system | user | assistant
- content: string
```

For v0, keep message content as text.

Out of scope for v0:

- image parts
- audio parts
- file parts
- tool calls
- function results
- multi-part content arrays

### 7.4 ProviderRequestOptions

```text
ProviderRequestOptions
- temperature?: number
- maxTokens?: number
- timeoutMs?: number
- seed?: number
```

Optional future fields, not required in v0:

```text
- topP
- frequencyPenalty
- presencePenalty
- stopSequences
- responseFormat
- toolChoice
```

Do not add these until needed by an approved feature.

### 7.5 Request Validation Boundary

General validation belongs outside the provider adapter.

Examples of general validation:

- request contains at least one message
- model is allowed
- provider is enabled
- maxTokens is within allowed bounds
- temperature is within allowed bounds

Provider-specific validation may occur inside the adapter only when the provider has unique constraints.

Example:

```text
This provider does not support seed.
This provider does not support this model.
This provider requires a non-empty user message.
```

---

## 8. Normalized Provider Response

### 8.1 Purpose

`ProviderResponse` is the provider-independent result returned by every provider adapter.

### 8.2 Suggested Shape

```text
ProviderResponse
- requestId: string
- provider: string
- model: string
- providerRequestId?: string
- content: string
- finishReason: ProviderFinishReason
- usage?: ProviderUsage
- metadata: map<string, string | number | boolean>
```

### 8.3 Finish Reasons

Normalize provider-specific finish reasons into this internal set:

```text
ProviderFinishReason
- stop
- length
- content_filter
- tool_call
- error
- unknown
```

For v0, `tool_call` may exist as a normalized enum value but tool-calling behavior remains out of scope.

### 8.4 Response Metadata

Metadata may include provider-level identifiers that are useful for diagnostics.

Allowed metadata examples:

```text
- providerResponseId
- providerCreatedAt
- providerModelVersion
- safetyStatus
```

Do not put secrets in response metadata.

---

## 9. Normalized Usage

### 9.1 Purpose

Usage represents provider-reported token usage and optional estimated cost.

### 9.2 Suggested Shape

```text
ProviderUsage
- inputTokens?: number
- outputTokens?: number
- totalTokens?: number
- estimatedCost?: decimal
- currency?: string
```

### 9.3 Token Mapping

Provider-specific token fields must be mapped into normalized fields.

Examples:

```text
prompt_tokens       -> inputTokens
completion_tokens   -> outputTokens
total_tokens        -> totalTokens
input_tokens        -> inputTokens
output_tokens       -> outputTokens
```

### 9.4 Cost Calculation

Cost calculation is optional in v0.

If implemented, it should be calculated outside provider-specific SDK response objects using configured model pricing.

The adapter may return token usage. A separate usage/cost service may calculate cost.

Recommended boundary:

```text
Provider adapter extracts tokens.
Usage/cost service estimates cost.
Trace logger persists usage/cost.
```

Do not hardcode pricing inside provider adapters unless there is no other option for v0.

---

## 10. Normalized Errors

### 10.1 Purpose

Provider errors must be normalized so Conexus can safely return consistent client errors and store useful trace details.

### 10.2 ProviderError Shape

```text
ProviderError
- code: ProviderErrorCode
- message: string
- provider: string
- model?: string
- providerRequestId?: string
- retryable: boolean
- rawStatusCode?: number
- safeDetails?: map<string, string | number | boolean>
```

### 10.3 ProviderErrorCode

Normalized provider error codes:

```text
ProviderConfigurationError
ProviderAuthenticationError
ProviderAuthorizationError
ProviderRateLimitError
ProviderTimeoutError
ProviderUnavailableError
ProviderInvalidRequestError
ProviderContentFilteredError
ProviderResponseError
ProviderUnknownError
```

### 10.4 Error Mapping Rules

Provider-specific exceptions/statuses should be mapped into stable internal categories.

Examples:

```text
401 / invalid API key
  -> ProviderAuthenticationError

403 / permission denied
  -> ProviderAuthorizationError

429 / rate limit
  -> ProviderRateLimitError

408 / timeout / cancellation due to timeout
  -> ProviderTimeoutError

5xx provider errors
  -> ProviderUnavailableError or ProviderResponseError

invalid model / malformed provider request
  -> ProviderInvalidRequestError

content policy refusal or safety block
  -> ProviderContentFilteredError
```

### 10.5 Safe Error Exposure

Provider adapters may capture raw provider errors internally, but client-facing errors must be safe.

Do not expose:

- API keys
- full raw provider payloads
- stack traces
- internal configuration values
- sensitive request content

Client-facing error responses should include:

- stable error code
- safe message
- trace id if available

---

## 11. Provider Capabilities

### 11.1 Purpose

Provider capabilities describe what a provider/model supports.

In v0, capabilities should stay simple.

### 11.2 Suggested Shape

```text
ProviderCapabilities
- providerKey: string
- supportedModels: string[]
- supportsStreaming: boolean
- supportsToolCalling: boolean
- supportsStructuredOutput: boolean
- supportsJsonMode: boolean
- supportsVision: boolean
- supportsAudio: boolean
```

For v0, most advanced flags may be false or informational only.

### 11.3 Model Capabilities

If needed, capabilities can be model-specific:

```text
ModelCapabilities
- providerKey: string
- modelName: string
- contextWindow?: number
- maxOutputTokens?: number
- supportsStreaming: boolean
- supportsToolCalling: boolean
- supportsStructuredOutput: boolean
```

Do not overbuild this in v0. Configuration-based capabilities are enough.

---

## 12. Provider Registry

### 12.1 Purpose

The provider registry maps provider keys to adapter instances.

Conceptual shape:

```text
ProviderRegistry
- get(providerKey): ProviderAdapter
- list(): ProviderAdapter[]
- exists(providerKey): boolean
```

### 12.2 Responsibilities

The registry should:

- expose enabled provider adapters
- reject unknown provider keys
- allow the router/execution service to retrieve adapters

### 12.3 Non-Responsibilities

The registry should not:

- decide which provider/model should be used for a request
- call providers directly
- know about prompt templates
- know about trace persistence

Routing belongs to the model router. Execution belongs to the execution service.

---

## 13. Model Router Interaction

### 13.1 Responsibility Split

The model router selects provider/model.

The provider adapter executes the selected provider/model request.

```text
ModelRouter decides: OpenAI + gpt-x
ProviderAdapter executes: OpenAI call for gpt-x
```

### 13.2 v0 Routing Rules

For v0, routing should be deterministic and simple:

1. If request explicitly specifies allowed provider/model, use it.
2. If no provider/model is specified, use configured default.
3. If provider is unknown, reject request.
4. If model is unknown or unsupported by provider, reject request.
5. Record the selected provider/model in trace.

### 13.3 Forbidden v0 Routing Behavior

Do not implement in v0:

- automatic fallback to another provider
- retry on a different model
- latency-aware model switching
- quality-aware model selection
- cost-based model substitution
- prompt-classification-based routing

These are future router capabilities, not provider abstraction responsibilities.

---

## 14. Execution Service Interaction

### 14.1 LlmExecutionService Role

The execution service coordinates the request lifecycle.

Conceptual flow:

```text
1. Receive validated LLM request.
2. Resolve prompt if needed.
3. Ask model router for provider/model decision.
4. Build ProviderRequest.
5. Retrieve adapter from ProviderRegistry.
6. Execute adapter.
7. Normalize/convert response to public LLM response.
8. Record trace.
9. Return response.
```

### 14.2 Adapter Role Inside Execution

The adapter handles only provider communication.

```text
ProviderRequest
  -> provider-specific request
  -> provider API/SDK call
  -> provider-specific response/error
  -> ProviderResponse or ProviderError
```

---

## 15. Timeout, Retry, and Cancellation

### 15.1 Timeout

v0 should support a basic timeout.

Timeout may be configured globally and optionally overridden per request within allowed limits.

Recommended fields:

```text
DefaultProviderTimeoutMs
MaxProviderTimeoutMs
```

### 15.2 Cancellation

If the backend framework supports cancellation tokens, the provider adapter should accept them.

Cancellation should propagate to provider SDK/API calls where possible.

### 15.3 Retry

Automatic retry is optional and should be conservative in v0.

Recommended v0 stance:

- no automatic retry by default
- classify retryable errors for future use
- do not retry non-idempotent or ambiguous requests unless explicitly designed

If retry is added, it should be done outside individual adapters through a shared resilience policy, not copied per provider.

---

## 16. OpenAI Adapter v0

### 16.1 Purpose

The OpenAI adapter is the first concrete provider implementation.

It proves that the provider abstraction works with a real provider while keeping OpenAI-specific logic isolated.

### 16.2 Responsibilities

The OpenAI adapter must:

- receive normalized ProviderRequest
- map normalized messages to OpenAI-compatible request format
- pass model name
- pass supported options such as temperature and max tokens where applicable
- call the OpenAI SDK/API
- map response content to normalized content
- map token usage to ProviderUsage
- map finish reason to ProviderFinishReason
- map OpenAI errors to ProviderError

### 16.3 OpenAI-Specific Logic Location

OpenAI-specific logic should live only under an infrastructure/provider-specific area.

Example:

```text
/infrastructure/providers/openai
```

OpenAI SDK types should not appear in application or domain layers.

### 16.4 OpenAI Adapter Tests

Tests should verify:

- messages are mapped correctly
- model name is passed correctly
- temperature/max tokens are passed correctly when provided
- successful response is normalized
- token usage is normalized
- finish reason is normalized
- authentication error is normalized
- rate limit error is normalized
- timeout error is normalized
- unknown provider error is normalized safely

Real OpenAI calls should not be required for standard automated tests.

---

## 17. Fake Provider Adapter

### 17.1 Purpose

A fake provider adapter should be available for tests.

It allows the execution flow to be tested without external API calls.

### 17.2 Required Behavior

The fake provider should support:

- deterministic successful response
- deterministic failed response
- configurable token usage
- configurable latency if useful
- support/unsupported model behavior

### 17.3 Example Behavior

```text
FakeProviderAdapter
- providerKey: fake
- supportedModels: fake-chat-model
- execute(request)
  - if metadata.forceError == true -> throw normalized error
  - else return content: "fake response"
```

Use this in unit/integration tests for the request lifecycle.

---

## 18. Public API Relationship

The public Conexus API should not expose provider adapter internals.

Public request:

```json
{
  "mode": "direct",
  "messages": [
    { "role": "user", "content": "Summarize this." }
  ],
  "model": {
    "provider": "openai",
    "name": "gpt-5.5"
  }
}
```

Internal provider request:

```text
ProviderRequest
- provider: openai
- model: gpt-5.5
- messages: normalized messages
- options: normalized options
```

Public response:

```json
{
  "requestId": "req_123",
  "traceId": "trace_456",
  "provider": "openai",
  "model": "gpt-5.5",
  "content": "...",
  "finishReason": "stop",
  "usage": {
    "inputTokens": 100,
    "outputTokens": 50,
    "totalTokens": 150
  }
}
```

Do not expose raw provider responses unless a debug mode is explicitly designed and protected.

---

## 19. Trace Logging Relationship

Provider abstraction must support trace logging but should not perform persistence directly.

The execution service or trace service should record:

```text
- request id
- trace id
- provider
- model
- provider request id if available
- status
- start time
- end time
- latency
- token usage
- estimated cost if available
- normalized error code if failed
```

Adapter returns the data. Trace service persists it.

Forbidden:

```text
OpenAiProviderAdapter writes directly to trace database.
```

Allowed:

```text
OpenAiProviderAdapter returns ProviderResponse with usage and providerRequestId.
LlmExecutionService passes data to TraceService.
```

---

## 20. Content Logging Policy

Provider adapters should not decide content logging policy.

Content logging belongs to trace/logging configuration.

The adapter may return content as part of the normal response. The trace service decides whether to store:

```text
none
metadata only
redacted snippets
full request/response
```

Default recommendation:

```text
metadata only
```

Provider adapters must not log raw prompts/responses to console or application logs unless explicitly configured through shared logging policy.

---

## 21. Configuration

### 21.1 Provider Configuration

Recommended configuration shape:

```text
Providers
- OpenAI
  - Enabled
  - ApiKey
  - BaseUrl optional
  - DefaultModel
  - AllowedModels
  - TimeoutMs
```

### 21.2 Model Configuration

Recommended configuration shape:

```text
Models
- provider: openai
  name: gpt-5.5
  enabled: true
  inputCostPerToken: optional
  outputCostPerToken: optional
  contextWindow: optional
```

### 21.3 Secrets

Provider API keys must not be committed.

Allowed:

- environment variables
- secret manager
- deployment secret store
- local developer secret configuration ignored by source control

Forbidden:

- API keys in source code
- API keys in checked-in config files
- API keys in traces
- API keys in admin UI

---

## 22. Testing Requirements

### 22.1 Unit Tests

Required unit tests:

```text
ProviderRegistry
- returns adapter for known enabled provider
- rejects unknown provider

ProviderCapabilities
- reports supported models correctly

Model support
- supportsModel returns true for configured model
- supportsModel returns false for unknown model

Request mapping
- normalized messages map to provider request
- options map correctly

Response mapping
- provider content maps to normalized content
- token usage maps to ProviderUsage
- finish reason maps to ProviderFinishReason

Error mapping
- authentication error maps correctly
- rate limit error maps correctly
- timeout maps correctly
- provider unavailable maps correctly
- unknown error maps safely
```

### 22.2 Integration Tests

Required integration tests using fake provider:

```text
Direct request lifecycle succeeds.
Direct request lifecycle failure produces normalized error.
Unsupported provider/model is rejected before provider call.
Successful provider response creates successful trace.
Failed provider response creates failed trace.
```

### 22.3 Contract Tests

Every concrete provider adapter should pass shared contract tests.

Example contract expectations:

```text
Given a valid ProviderRequest,
adapter returns ProviderResponse with provider, model, content, and finishReason.

Given an unsupported model,
adapter rejects or reports unsupported according to contract.

Given a provider authentication failure,
adapter maps it to ProviderAuthenticationError.
```

### 22.4 Real Provider Smoke Test

Optional manual smoke test:

```text
Submit one direct request through OpenAI adapter using a test API key.
Verify normalized response and trace.
```

This should not be required for CI.

---

## 23. Acceptance Criteria

Provider abstraction v0 is accepted when:

1. A stable provider adapter interface exists.
2. Normalized provider request and response types exist.
3. Normalized usage and error types exist.
4. A provider registry can resolve enabled adapters by key.
5. The model router can validate provider/model support through the abstraction.
6. The execution service can call a provider without knowing provider SDK details.
7. At least one fake provider exists for tests.
8. At least one real provider adapter exists, preferably OpenAI.
9. Provider-specific SDK types do not leak outside infrastructure adapter code.
10. Provider errors are mapped into normalized errors.
11. Successful responses include normalized content and usage when available.
12. Tests prove success, failure, unsupported model, and error mapping behavior.
13. No real provider call is required for normal automated tests.
14. Trace logging receives provider/model/usage/error metadata through normalized objects.

---

## 24. Implementation Sequence

Recommended implementation order:

```text
1. Define normalized provider domain types.
2. Define provider adapter interface.
3. Define provider capabilities model.
4. Implement provider registry.
5. Implement fake provider adapter.
6. Add unit tests for registry and fake provider.
7. Implement simple model router integration.
8. Implement execution service path using fake provider.
9. Add integration tests for request lifecycle.
10. Implement OpenAI adapter.
11. Add OpenAI adapter mapping tests with mocked SDK/API responses.
12. Wire OpenAI adapter through configuration.
13. Add optional manual smoke test.
```

Do not begin with the real provider SDK before the internal contract and fake provider are working.

---

## 25. SPDD Canvas Required Before Coding

Before implementing this spec, create a REASONS Canvas at:

```text
/docs/ai/reasons-canvases/provider-abstraction-v0.md
```

The Canvas must include:

```text
R — Requirements
E — Entities
A — Approach
S — Structure
O — Operations
N — Norms
S — Safeguards
```

The implementation agent must reference both:

```text
/docs/product/conexus-v0-scope.md
/docs/specs/provider-abstraction.md
```

No implementation should proceed from a vague prompt such as:

```text
Add provider abstraction.
```

Use bounded implementation prompts only.

---

## 26. Non-Negotiable Safeguards

The implementation must obey these safeguards:

1. Do not call provider SDKs outside provider adapter implementations.
2. Do not add streaming in v0.
3. Do not add tool calling in v0.
4. Do not add fallback routing in v0.
5. Do not hardcode API keys.
6. Do not log raw request/response content by default.
7. Do not make real provider calls in automated tests.
8. Do not introduce broad architecture changes unrelated to provider abstraction.
9. Do not make the provider adapter responsible for prompt rendering.
10. Do not make the provider adapter responsible for trace persistence.
11. Do not expose raw provider errors to public API clients.
12. Do not allow provider-specific SDK types to leak into application/domain layers.

---

## 27. Example Implementation Prompt

Use this prompt with Cursor, Claude Code, Codex, or another coding agent:

```text
We are implementing Conexus provider abstraction v0.

Read:
- /docs/product/conexus-v0-scope.md
- /docs/specs/provider-abstraction.md
- /docs/ai/reasons-canvases/provider-abstraction-v0.md

Task:
Implement only the provider abstraction foundation.

Scope:
- normalized ProviderRequest
- normalized ProviderResponse
- ProviderUsage
- ProviderError
- ProviderCapabilities
- provider adapter interface
- provider registry
- fake provider adapter for tests
- tests for registry, fake provider, request/response/error behavior

Do not implement:
- streaming
- tool calling
- fallback routing
- advanced model routing
- admin UI
- prompt registry
- real provider SDK integration unless the foundation is complete

Before editing:
1. Inspect the repo structure.
2. Identify the smallest safe file locations.
3. Show intended files to add/change.
4. Show a short patch strategy.

After editing:
1. Run relevant tests.
2. Report changed files.
3. Report any deviations from the spec.
4. Report remaining risks.
```

---

## 28. Open Questions

These decisions should be resolved before or during the first REASONS Canvas:

1. What is the current backend stack and folder convention?
2. Should provider configuration be database-backed or config-file based in v0?
3. Should model definitions live in config, database, or code constants for v0?
4. What authentication model protects the Conexus API?
5. What test framework is standard in the repo?
6. Should estimated cost be included in v0 or deferred?
7. Should raw request/response content ever be stored in traces during local development?

Unless there is a strong reason otherwise, v0 should choose the simplest option that preserves the provider boundary.

---

## 29. Final Boundary Statement

The provider abstraction is successful when Conexus can execute an LLM request through a provider without the rest of the system knowing anything about the provider SDK.

The correct v0 outcome is:

```text
One internal contract.
One fake provider for tests.
One real provider adapter.
No provider leakage.
No speculative complexity.
```

This is the foundation for everything Conexus may become later.

