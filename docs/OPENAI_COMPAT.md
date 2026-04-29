# OpenAI compatibility (Conexus)

Conexus implements a **basic** OpenAI-compatible `POST /v1/chat/completions` endpoint for text-only chat completions, including **SSE streaming**.

## Base URL and auth

- **Base URL**: `http://localhost:8000/v1`
- **API key**: use a **Project API key** created in the Conexus back-office (`cx_live_*`)

OpenAI SDK configuration is typically:

- **Python**: `OpenAI(base_url="http://localhost:8000/v1", api_key="<cx_live_...>")`
- **TypeScript**: `new OpenAI({ baseURL: "http://localhost:8000/v1", apiKey: "<cx_live_...>" })`

## Supported endpoint

- **Chat Completions**: `POST /v1/chat/completions`
  - **Non-streaming**: returns an OpenAI-shaped `chat.completion`
  - **Streaming**: returns `text/event-stream` with `chat.completion.chunk` events and a final `data: [DONE]`

## Supported request fields

Required:

- `model` (string)
- `messages` (array of `{role, content}`)

Supported and forwarded to providers:

- `max_tokens`
- `temperature`

Accepted for OpenAI client compatibility (**accepted but not forwarded** by Conexus today):

- `top_p`
- `stop`
- `user`
- `seed`
- `presence_penalty`
- `frequency_penalty`

Compatibility validation:

- `n`: allowed when missing or `n=1`; **rejected** when `n>1`
- `response_format`: accepted only when `{"type":"text"}` or when `type` is omitted
- `stream`: when `true`, Conexus streams SSE; when `false`/missing, normal JSON response

## Unsupported request fields (clear 400)

Conexus intentionally does **not** implement these yet:

- `tools`, `tool_choice` (**tool calls are not supported yet**)
- `logprobs`, `top_logprobs` (**logprobs are not supported yet**)
- `n > 1` (**only n=1 is supported**)

Conexus does **not** implement:

- tool calls / function calling
- multimodal / vision inputs
- Assistants API

## Streaming behavior

When `stream=true`:

- Conexus authenticates the project API key as usual
- Hard project limits are enforced **before** contacting the provider
- A `gateway_requests` row is created **before** streaming begins
- The response is SSE with `chat.completion.chunk` `data:` payloads
- The stream ends with `data: [DONE]`
- The response includes `X-Conexus-Request-Id` so you can correlate the BO log row

Request logging notes:

- Conexus **does not store prompt or response bodies** (including streamed content).
- If token usage is available from the provider stream, Conexus stores tokens and estimated cost; otherwise those fields remain null.
- Some compatibility-validation 400s may include `X-Conexus-Request-Id` but **may not create** a `gateway_requests` row (the BO request log is only for calls that reach the gateway service).
- When a streaming error occurs after the SSE response has started, Conexus may emit a best-effort SSE `error` object; **the BO request status is authoritative**.

## Known limitations

- Only `n=1`
- No tool calls
- No logprobs
- `response_format` only supports plain text mode
- **Concrete OpenAI models** stream (for example `gpt-4o-mini`)
- **Concrete Anthropic models** stream (for example `claude-sonnet-4-20250514`)
- **Conexus alias streaming** streams via the alias’ **Anthropic primary** model
- Streaming does **not** do mid-stream fallback (once streaming starts, Conexus never switches providers). OpenAI fallback remains available only for **non-streaming** alias calls.

