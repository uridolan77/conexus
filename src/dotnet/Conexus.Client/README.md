# Conexus.Client (.NET)

Minimal **HttpClient**-based client for the Conexus gateway as implemented today:

- `GET /health`
- `GET /readyz`
- `POST /v1/chat/completions` (non-streaming JSON responses only)

There is **no** embedding, route preview, models listing, or usage/trace retrieval in this client — those endpoints are not implemented on the public API yet (see `docs/readiness/CONEXUS_APP_INTEGRATION_READINESS.md`).

**No OpenAI/Anthropic/Gemini SDK references** are included.

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
```

## Optional gateway headers

This client does not yet expose helpers for `X-Conexus-Domain-Key` or `X-Conexus-Gateway-Profile-Id`. Configure them on the underlying `HttpClient` if needed, or extend the wrapper in your application code.

## Build

```bash
dotnet build
```

Target framework: **net8.0**.
