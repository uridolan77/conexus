using System.Text.Json;

namespace Conexus.Client;

internal static class ConexusJson
{
    /// <summary>Matches FastAPI/Pydantic default JSON field names (snake_case).</summary>
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DictionaryKeyPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
    };
}
