"""ConexusClient: async HTTP client for /v1/chat/completions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class ConexusMessage:
    role: str
    content: str


@dataclass
class ConexusUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ConexusResponse:
    id: str
    model: str
    content: str
    finish_reason: str
    usage: ConexusUsage
    raw: dict[str, Any] = field(default_factory=dict)


class ConexusClientError(Exception):
    """Raised when Conexus returns an error or the request fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ConexusClient:
    """Async HTTP client for Conexus /v1/chat/completions.

    Usage::

        async with ConexusClient(base_url="http://localhost:8000", api_key="cx_...") as client:
            response = await client.chat(
                model="conexus-fast",
                messages=[{"role": "user", "content": "Hello"}],
            )
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 120.0,
        _http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        # Inject a custom client for tests; create one otherwise.
        self._http: httpx.AsyncClient = _http_client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )
        self._owns_client = _http_client is None

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        extra: dict[str, Any] | None = None,
    ) -> ConexusResponse:
        """Send a chat completion request to Conexus.

        Args:
            model: Conexus model alias, e.g. ``conexus-fast``.
            messages: OpenAI-compatible message list.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.
            extra: Additional body fields forwarded verbatim.

        Returns:
            A :class:`ConexusResponse` with the assistant reply.

        Raises:
            ConexusClientError: On HTTP error or Conexus error envelope.
        """
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if extra:
            body.update(extra)

        try:
            response = await self._http.post(
                "/v1/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        except httpx.RequestError as exc:
            raise ConexusClientError(f"Request failed: {exc}") from exc

        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise ConexusClientError(
                f"Conexus returned {response.status_code}: {detail}",
                status_code=response.status_code,
            )

        data: dict[str, Any] = response.json()

        try:
            choice = data["choices"][0]
            usage_raw = data.get("usage", {})
            return ConexusResponse(
                id=data["id"],
                model=data["model"],
                content=choice["message"]["content"],
                finish_reason=choice.get("finish_reason", ""),
                usage=ConexusUsage(
                    prompt_tokens=usage_raw.get("prompt_tokens", 0),
                    completion_tokens=usage_raw.get("completion_tokens", 0),
                    total_tokens=usage_raw.get("total_tokens", 0),
                ),
                raw=data,
            )
        except (KeyError, IndexError) as exc:
            raise ConexusClientError(
                f"Unexpected Conexus response shape: {exc}"
            ) from exc

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> "ConexusClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
