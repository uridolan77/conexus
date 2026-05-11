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
        CreateChatCompletionAsync(request, default, cancellationToken);

    public Task<ChatCompletionResponse> CreateChatCompletionAsync(
        ChatCompletionRequest request,
        ChatCompletionCallOptions options,
        CancellationToken cancellationToken = default) =>
        PostChatCompletionAsync(request, options, cancellationToken);

    private async Task<T> GetAsync<T>(string path, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync(path, cancellationToken).ConfigureAwait(false);
        return await ReadOrThrowAsync<T>(response, cancellationToken).ConfigureAwait(false);
    }

    private async Task<ChatCompletionResponse> PostChatCompletionAsync(
        ChatCompletionRequest request,
        ChatCompletionCallOptions options,
        CancellationToken cancellationToken)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, "/v1/chat/completions")
        {
            Content = JsonContent.Create(request, options: ConexusJson.Options),
        };
        if (!string.IsNullOrEmpty(options.RequestId))
        {
            req.Headers.TryAddWithoutValidation("X-Conexus-Request-Id", options.RequestId);
        }

        using var response = await _httpClient.SendAsync(req, cancellationToken).ConfigureAwait(false);
        return await ReadOrThrowAsync<ChatCompletionResponse>(response, cancellationToken).ConfigureAwait(false);
    }

    private static async Task<T> ReadOrThrowAsync<T>(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        var responseRequestId = GetRequestIdHeader(response);

        if (response.IsSuccessStatusCode)
        {
            var value = await response.Content
                .ReadFromJsonAsync<T>(ConexusJson.Options, cancellationToken)
                .ConfigureAwait(false);
            return value ?? throw new ConexusClientException(
                "Conexus returned an empty response body.",
                statusCode: (int)response.StatusCode,
                responseBody: null,
                responseRequestId: responseRequestId);
        }

        var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
        throw new ConexusClientException(
            $"Conexus request failed with status {(int)response.StatusCode} {response.ReasonPhrase}.",
            statusCode: (int)response.StatusCode,
            responseBody: body,
            responseRequestId: responseRequestId);
    }

    private static string? GetRequestIdHeader(HttpResponseMessage response)
    {
        if (!response.Headers.TryGetValues("X-Conexus-Request-Id", out var values))
        {
            return null;
        }

        return values.FirstOrDefault();
    }
}

public sealed class ConexusClientException : Exception
{
    public int? StatusCode { get; }
    public string? ResponseBody { get; }
    public string? ResponseRequestId { get; }

    public ConexusClientException(
        string message,
        int? statusCode = null,
        string? responseBody = null,
        string? responseRequestId = null)
        : base(message)
    {
        StatusCode = statusCode;
        ResponseBody = responseBody;
        ResponseRequestId = responseRequestId;
    }
}
