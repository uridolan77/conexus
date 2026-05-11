namespace Conexus.Client;

public sealed record HealthResponse(string Status, string Service, string Version);

public sealed record ReadyResponse(string Status, IReadOnlyDictionary<string, bool>? Checks);

public sealed record ChatMessage(string Role, string Content);

public sealed record ChatCompletionRequest(
    string Model,
    IReadOnlyList<ChatMessage> Messages,
    int? MaxTokens = null,
    double? Temperature = null,
    bool? Stream = null);

public sealed record ChatChoice(
    int Index,
    ChatMessage Message,
    string FinishReason);

public sealed record TokenUsage(int PromptTokens, int CompletionTokens, int TotalTokens);

public sealed record ChatCompletionResponse(
    string Id,
    string Object,
    long Created,
    string Model,
    string Provider,
    bool FallbackUsed,
    IReadOnlyList<ChatChoice> Choices,
    TokenUsage Usage);
