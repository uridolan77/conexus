"""ToolClient: abstract base for external tool access.

Concrete implementations can read from the local filesystem, call MCP servers,
query APIs, run shell commands, etc. The interface is intentionally minimal so
workflows can stub it in tests without any I/O.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result of a tool invocation."""

    tool_name: str
    content: str
    metadata: dict[str, object] | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class ToolClient(ABC):
    """Abstract base for tool invocation."""

    @abstractmethod
    async def invoke(self, tool_name: str, **kwargs: object) -> ToolResult:
        """Invoke a named tool with keyword arguments."""

    async def aclose(self) -> None:
        """Release resources. Override if the implementation holds connections."""

    async def __aenter__(self) -> "ToolClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()


class StubToolClient(ToolClient):
    """In-memory stub tool client for tests.

    Registered responses are returned by name; any unregistered tool
    returns a ToolResult with ``content=""`` so workflows can still run.
    """

    def __init__(self) -> None:
        self._responses: dict[str, ToolResult] = {}

    def register(self, tool_name: str, result: ToolResult) -> None:
        self._responses[tool_name] = result

    async def invoke(self, tool_name: str, **kwargs: object) -> ToolResult:
        if tool_name in self._responses:
            return self._responses[tool_name]
        return ToolResult(tool_name=tool_name, content="")


class FilesystemToolClient(ToolClient):
    """Simple filesystem tool client for reading local files.

    Supported tools:
    - ``read_file(path: str)`` — read a file as text
    - ``list_dir(path: str)`` — list directory entries
    """

    async def invoke(self, tool_name: str, **kwargs: object) -> ToolResult:
        import os

        if tool_name == "read_file":
            path = str(kwargs.get("path", ""))
            try:
                with open(path, encoding="utf-8") as fh:
                    content = fh.read()
                return ToolResult(tool_name=tool_name, content=content)
            except OSError as exc:
                return ToolResult(tool_name=tool_name, content="", error=str(exc))

        if tool_name == "list_dir":
            path = str(kwargs.get("path", "."))
            try:
                entries = os.listdir(path)
                content = "\n".join(entries)
                return ToolResult(tool_name=tool_name, content=content)
            except OSError as exc:
                return ToolResult(tool_name=tool_name, content="", error=str(exc))

        return ToolResult(
            tool_name=tool_name,
            content="",
            error=f"Unknown tool: {tool_name}",
        )
