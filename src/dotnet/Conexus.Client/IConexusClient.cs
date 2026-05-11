namespace Conexus.Client;

/// <summary>Per-call options for <see cref="IConexusClient.CreateChatCompletionAsync"/>.</summary>
public readonly record struct ChatCompletionCallOptions(string? RequestId = null);

/// <summary>Client for the implemented public Conexus gateway surface only.</summary>
public interface IConexusClient
{
    Task<HealthResponse> GetHealthAsync(CancellationToken cancellationToken = default);

    /// <summary>Calls GET /readyz (same payload as GET /health/ready).</summary>
    Task<ReadyResponse> GetReadyAsync(CancellationToken cancellationToken = default);

    Task<ChatCompletionResponse> CreateChatCompletionAsync(
        ChatCompletionRequest request,
        CancellationToken cancellationToken = default);

    Task<ChatCompletionResponse> CreateChatCompletionAsync(
        ChatCompletionRequest request,
        ChatCompletionCallOptions options,
        CancellationToken cancellationToken = default);
}
