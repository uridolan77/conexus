using System.Net.Http.Json;
using System.Text.Json;

namespace Conexus.Client;

public sealed class ConexusClient : IConexusClient
{
    private readonly HttpClient _httpClient;

    public ConexusClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public Task<HealthResponse> GetHealthAsync(CancellationToken cancellationToken = default) =>
        GetAsync<HealthResponse>("/health", cancellationToken);

    public Task<ReadyResponse> GetReadyAsync(CancellationToken cancellationToken = default) =>
        GetAsync<ReadyResponse>("/readyz", cancellationToken);

    public Task<ChatCompletionResponse> CreateChatCompletionAsync(
        ChatCompletionRequest request,
        CancellationToken cancellationToken = default) =>
        PostAsync<ChatCompletionRequest, ChatCompletionResponse>(
            "/v1/chat/completions",
            request,
            cancellationToken);

    private async Task<T> GetAsync<T>(string path, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync(path, cancellationToken).ConfigureAwait(false);
        return await ReadOrThrowAsync<T>(response, cancellationToken).ConfigureAwait(false);
    }

    private async Task<TResponse> PostAsync<TRequest, TResponse>(
        string path,
        TRequest request,
        CancellationToken cancellationToken)
    {
        using var response = await _httpClient
            .PostAsJsonAsync(path, request, ConexusJson.Options, cancellationToken)
            .ConfigureAwait(false);
        return await ReadOrThrowAsync<TResponse>(response, cancellationToken).ConfigureAwait(false);
    }

    private static async Task<T> ReadOrThrowAsync<T>(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        if (response.IsSuccessStatusCode)
        {
            var value = await response.Content
                .ReadFromJsonAsync<T>(ConexusJson.Options, cancellationToken)
                .ConfigureAwait(false);
            return value ?? throw new ConexusClientException("Conexus returned an empty response body.");
        }

        var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
        throw new ConexusClientException(
            $"Conexus request failed with status {(int)response.StatusCode} {response.ReasonPhrase}. Body: {body}",
            (int)response.StatusCode,
            body);
    }
}

public sealed class ConexusClientException : Exception
{
    public int? StatusCode { get; }
    public string? ResponseBody { get; }

    public ConexusClientException(string message, int? statusCode = null, string? responseBody = null)
        : base(message)
    {
        StatusCode = statusCode;
        ResponseBody = responseBody;
    }
}
