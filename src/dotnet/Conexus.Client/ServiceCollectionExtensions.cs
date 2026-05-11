using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;

namespace Conexus.Client;

public sealed class ConexusClientOptions
{
    public string BaseUrl { get; set; } = "http://localhost:8000";

    /// <summary>Project API key (Bearer) for gateway calls.</summary>
    public string? ApiKey { get; set; }
}

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddConexusClient(
        this IServiceCollection services,
        Action<ConexusClientOptions> configure)
    {
        services.Configure(configure);

        services.AddHttpClient<IConexusClient, ConexusClient>((provider, client) =>
        {
            var options = provider.GetRequiredService<IOptions<ConexusClientOptions>>().Value;
            client.BaseAddress = new Uri(options.BaseUrl.TrimEnd('/'));
            if (!string.IsNullOrWhiteSpace(options.ApiKey))
            {
                client.DefaultRequestHeaders.Authorization =
                    new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", options.ApiKey!);
            }
        });

        return services;
    }
}
