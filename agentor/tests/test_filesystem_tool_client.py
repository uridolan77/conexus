"""Tests for FilesystemToolClient root restrictions and traversal rejection."""

from __future__ import annotations

from pathlib import Path

from agentor_runtime.clients.tool import FilesystemToolClient


async def test_read_source_file_allowed(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    f = root / "a.txt"
    f.write_text("hello", encoding="utf-8")

    client = FilesystemToolClient(allowed_roots=[str(root)])
    result = await client.read_source_file(str(f))

    assert result.ok is True
    assert result.content == "hello"


async def test_read_source_file_missing_file_returns_error(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    missing = root / "missing.txt"

    client = FilesystemToolClient(allowed_roots=[str(root)])
    result = await client.read_source_file(str(missing))

    assert result.ok is False
    assert result.error is not None


async def test_read_source_file_rejects_path_traversal(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()

    client = FilesystemToolClient(allowed_roots=[str(root)])
    result = await client.read_source_file(str(root / ".." / "secrets.txt"))

    assert result.ok is False
    assert result.error is not None
    assert "traversal" in result.error.lower()


async def test_read_source_file_rejects_outside_root(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")

    client = FilesystemToolClient(allowed_roots=[str(root)])
    result = await client.read_source_file(str(outside))

    assert result.ok is False
    assert result.error is not None
    assert "outside" in result.error.lower()


async def test_search_sources_case_insensitive_and_extension_allowlist(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.md").write_text("Hello World", encoding="utf-8")
    (root / "b.json").write_text('{"k":"hello"}', encoding="utf-8")
    (root / "c.bin").write_bytes(b"\x00\x01hello\x02")  # should be ignored by ext allowlist

    client = FilesystemToolClient(allowed_roots=[str(root)])
    result = await client.search_sources("hello", limit=10)

    assert result.ok is True
    # Should match md and json, case-insensitive, but not .bin
    assert "a.md" in result.content
    assert "b.json" in result.content
    assert "c.bin" not in result.content

