"""ToolClient: abstract base for external tool access.

Concrete implementations can read from the local filesystem, call MCP servers,
query APIs, run shell commands, etc. The interface is intentionally minimal so
workflows can stub it in tests without any I/O.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


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

    async def read_source_file(self, path: str) -> ToolResult:
        return await self.invoke("read_source_file", path=path)

    async def search_sources(self, query: str, limit: int = 20) -> ToolResult:
        return await self.invoke("search_sources", query=query, limit=limit)

    async def list_collection(self, collection: str) -> ToolResult:
        return await self.invoke("list_collection", collection=collection)

    async def aclose(self) -> None:
        """Release resources. Override if the implementation holds connections."""

    async def __aenter__(self) -> "ToolClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()


class StubToolClient(ToolClient):
    """In-memory stub tool client for tests.

    Registered responses can be keyed by tool name and expected kwargs; any
    unregistered tool returns a ToolResult with ``content=""`` so workflows can
    still run.
    """

    def __init__(self) -> None:
        self._responses: list[tuple[str, dict[str, object], ToolResult]] = []

    def register(self, tool_name: str, result: ToolResult, **match_kwargs: object) -> None:
        """Register a response for a tool.

        If match_kwargs are provided, the response is returned only when the invoked
        kwargs include those exact key/value pairs (subset match). If no match_kwargs
        are provided, the response is used as a default for that tool name.
        """
        self._responses.append((tool_name, dict(match_kwargs), result))

    async def invoke(self, tool_name: str, **kwargs: object) -> ToolResult:
        for name, match, result in self._responses:
            if name != tool_name:
                continue
            if all(kwargs.get(k) == v for k, v in match.items()):
                return result
        return ToolResult(tool_name=tool_name, content="")


class FilesystemToolClient(ToolClient):
    """Filesystem tool client restricted to an allowlist of root directories.

    All paths are resolved to their absolute real path before access.
    Any path that does not fall under one of the allowed roots is rejected
    with an error ToolResult rather than raising an exception, so workflows
    can handle the failure gracefully.

    Supported tools:
    - ``read_source_file(path: str)`` — read a file as text
    - ``search_sources(query: str, limit: int)`` — search text files under roots
    - ``list_collection(collection: str)`` — list directory entries under roots
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
        from pathlib import PurePath

        try:
            parts = PurePath(path).parts
        except Exception:
            parts = ()
        if ".." in parts:
            return "", "Path traversal is not allowed"

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

        if tool_name == "read_source_file":
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

        if tool_name == "list_collection":
            collection = str(kwargs.get("collection", "."))
            resolved, err = self._check_path(collection)
            if err:
                return ToolResult(tool_name=tool_name, content="", error=err)
            try:
                entries = os.listdir(resolved)
                content = "\n".join(entries)
                return ToolResult(tool_name=tool_name, content=content)
            except OSError as exc:
                return ToolResult(tool_name=tool_name, content="", error=str(exc))

        if tool_name == "search_sources":
            query = str(kwargs.get("query", "")).strip()
            limit = int(kwargs.get("limit", 20) or 20)
            if not query:
                return ToolResult(tool_name=tool_name, content="", error="Query is empty")
            if not self._allowed:
                return ToolResult(
                    tool_name=tool_name,
                    content="",
                    error="FilesystemToolClient has no allowed_roots configured",
                )

            # Keep this conservative for v0.1: case-insensitive substring search,
            # and only scan a small set of text-like extensions.
            query_lc = query.casefold()
            allowed_exts = {".md", ".mdx", ".txt", ".json"}

            matches: list[str] = []
            for root in self._allowed:
                for dirpath, _dirnames, filenames in os.walk(root):
                    for filename in filenames:
                        if len(matches) >= limit:
                            break
                        _, ext = os.path.splitext(filename)
                        if ext.lower() not in allowed_exts:
                            continue
                        path = os.path.join(dirpath, filename)
                        try:
                            with open(path, encoding="utf-8") as fh:
                                for idx, line in enumerate(fh, start=1):
                                    if query_lc in line.casefold():
                                        rel = os.path.relpath(path, root)
                                        matches.append(f"{rel}:{idx}:{line.rstrip()}")
                                        break
                        except OSError:
                            continue
                    if len(matches) >= limit:
                        break
                if len(matches) >= limit:
                    break

            return ToolResult(tool_name=tool_name, content="\n".join(matches))

        return ToolResult(
            tool_name=tool_name,
            content="",
            error=f"Unknown tool: {tool_name}",
        )
