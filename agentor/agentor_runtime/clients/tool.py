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
    """Filesystem tool client restricted to an allowlist of root directories.

    All paths are resolved to their absolute real path before access.
    Any path that does not fall under one of the allowed roots is rejected
    with an error ToolResult rather than raising an exception, so workflows
    can handle the failure gracefully.

    Supported tools:
    - ``read_file(path: str)`` — read a file as text
    - ``list_dir(path: str)`` — list directory entries
    """

    def __init__(self, allowed_roots: list[str] | None = None) -> None:
        """Create a FilesystemToolClient.

        Args:
            allowed_roots: Absolute directory paths that callers are allowed to
                           read under. Pass ``None`` only in fully-trusted
                           single-user contexts; the client will warn and refuse
                           all access if the list is empty.
        """
        import os

        if allowed_roots is None:
            # Default to nothing — callers must explicitly opt in.
            self._allowed: list[str] = []
        else:
            self._allowed = [os.path.realpath(r) for r in allowed_roots]

    def _check_path(self, path: str) -> tuple[str, str | None]:
        """Return (resolved_path, error_or_None).

        Rejects the path if it escapes every allowed root.
        """
        import os

        try:
            resolved = os.path.realpath(os.path.abspath(path))
        except (ValueError, OSError) as exc:
            return "", f"Invalid path: {exc}"

        if not self._allowed:
            return "", "FilesystemToolClient has no allowed_roots configured"

        for root in self._allowed:
            # Ensure the resolved path starts with root + sep to prevent
            # /allowed/prefix-but-different matching /allowed/prefix.
            if resolved == root or resolved.startswith(root + os.sep):
                return resolved, None

        return "", f"Path '{resolved}' is outside all allowed roots"

    async def invoke(self, tool_name: str, **kwargs: object) -> ToolResult:
        import os

        if tool_name == "read_file":
            path = str(kwargs.get("path", ""))
            resolved, err = self._check_path(path)
            if err:
                return ToolResult(tool_name=tool_name, content="", error=err)
            try:
                with open(resolved, encoding="utf-8") as fh:
                    content = fh.read()
                return ToolResult(tool_name=tool_name, content=content)
            except OSError as exc:
                return ToolResult(tool_name=tool_name, content="", error=str(exc))

        if tool_name == "list_dir":
            path = str(kwargs.get("path", "."))
            resolved, err = self._check_path(path)
            if err:
                return ToolResult(tool_name=tool_name, content="", error=err)
            try:
                entries = os.listdir(resolved)
                content = "\n".join(entries)
                return ToolResult(tool_name=tool_name, content=content)
            except OSError as exc:
                return ToolResult(tool_name=tool_name, content="", error=str(exc))

        return ToolResult(
            tool_name=tool_name,
            content="",
            error=f"Unknown tool: {tool_name}",
        )
