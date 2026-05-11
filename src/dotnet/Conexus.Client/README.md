# Conexus.Client (.NET)

Minimal **HttpClient**-based client for the Conexus gateway as implemented today:

- `GET /health`
- `GET /readyz`
- `POST /v1/chat/completions` (non-streaming JSON responses only)

There is **no** embedding, route preview, models listing, or usage/trace retrieval in this client — those endpoints are not implemented on the public API yet (see `docs/readiness/CONEXUS_APP_INTEGRATION_READINESS.md`).

**No OpenAI/Anthropic/Gemini SDK references** are included.

## `X-Conexus-Request-Id`: correlation only, not idempotency

`X-Conexus-Request-Id` is a **correlation identifier** for logs, support, and matching rows in the Conexus back office. It is **not** an idempotency or replay key.

- Use a **new** value for **each new** chat completion attempt (e.g. a UUID).
- Reusing a value that already exists on a previous gateway request returns **409** `request_id_conflict` from the API.
- If Conexus adds true idempotent retries later, expect a separate header such as `Idempotency-Key` — not this field.

## Retries and timeouts

On timeout or transport failure where the client **does not know** whether Conexus accepted the request:

- **Do not** blindly retry with the **same** `X-Conexus-Request-Id` unless your app explicitly treats **409** as “this id may already be in use / call may have landed.”
- For normal retries, generate a **new** Conexus request id per attempt.

**Recommended pattern**

- **Stable app id** (per workflow / agent run / Athanor operation): keep in your own telemetry and message metadata.
- **Conexus request id** (`X-Conexus-Request-Id` / response `request_id`): **unique per LLM call attempt** so each attempt maps to at most one gateway row and one BO line.

## Usage (dependency injection)

```csharp
using Conexus.Client;
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
services.AddConexusClient(o =>
{
    o.BaseUrl = "http://localhost:8000";
    o.ApiKey = Environment.GetEnvironmentVariable("CONEXUS_PROJECT_KEY");
});

await using var provider = services.BuildServiceProvider();
var conexus = provider.GetRequiredService<IConexusClient>();

var health = await conexus.GetHealthAsync();
Console.WriteLine($"{health.Service} {health.Version}");

var chat = await conexus.CreateChatCompletionAsync(new ChatCompletionRequest(
    Model: "conexus-fast",
    Messages: new[]
    {
        new ChatMessage("user", "Say hello in one short sentence."),
    },
    MaxTokens: 128,
    Temperature: 0.2));

Console.WriteLine(chat.Choices[0].Message.Content);
Console.WriteLine($"Conexus request_id: {chat.RequestId}");
```

Per-call correlation header (optional):

```csharp
var chat2 = await conexus.CreateChatCompletionAsync(
    new ChatCompletionRequest(
        Model: "conexus-fast",
        Messages: new[] { new ChatMessage("user", "Ping.") }),
    new ChatCompletionCallOptions(RequestId: Guid.NewGuid().ToString("N")));
```

On non-2xx responses, inspect `ConexusClientException.ResponseRequestId` when present (Conexus adds `X-Conexus-Request-Id` on most gateway errors).

## Optional gateway headers

This client does not yet expose helpers for `X-Conexus-Domain-Key` or `X-Conexus-Gateway-Profile-Id`. Configure them on the underlying `HttpClient` if needed, or extend the wrapper in your application code.

## Build

```bash
dotnet build
```

Target framework: **net8.0**.
