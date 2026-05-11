namespace Conexus.Client;

/// <summary>Client for the implemented public Conexus gateway surface only.</summary>
public interface IConexusClient
{
    Task<HealthResponse> GetHealthAsync(CancellationToken cancellationToken = default);

    /// <summary>Calls GET /readyz (same payload as GET /health/ready).</summary>
    Task<ReadyResponse> GetReadyAsync(CancellationToken cancellationToken = default);

    Task<ChatCompletionResponse> CreateChatCompletionAsync(
        ChatCompletionRequest request,
        CancellationToken cancellationToken = default);
}
