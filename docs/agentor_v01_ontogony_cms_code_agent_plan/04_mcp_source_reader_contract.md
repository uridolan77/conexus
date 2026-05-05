# 04 — MCP / Tool Source Reader Contract

## v0.1 interface

Keep `ToolClient` minimal but make tools explicit.

Required read-only tools:

```text
read_source_file(path: str) -> ToolResult
search_sources(query: str, limit: int = 10) -> ToolResult
list_collection(collection: str) -> ToolResult
validate_slug_refs(slugs: list[str]) -> ToolResult
```

Optional later tools:

```text
run_ontogony_check() -> ToolResult
write_file(path: str, content: str) -> ToolResult
open_pull_request(branch: str, title: str, body: str) -> ToolResult
```

## Safety rule

Only read tools are allowed before human approval.

Write/build tools must be behind approval.

## Filesystem fallback

A `FilesystemToolClient` is acceptable for local development, but it must be root-restricted.

Constructor:

```python
FilesystemToolClient(root: str | Path)
```

Path resolution:

```python
resolved = (root / requested_path).resolve()
if not resolved.is_relative_to(root.resolve()):
    reject
```

Reject absolute paths outside root, `../` traversal, empty paths, `.env`, private key files, and hidden directories unless explicitly allowed.

## MCP client later

Add `McpToolClient` later with the same interface:

```python
class McpToolClient(ToolClient):
    async def invoke(self, tool_name: str, **kwargs: object) -> ToolResult:
        ...
```

Do not implement full MCP server/client in this task unless already available.
