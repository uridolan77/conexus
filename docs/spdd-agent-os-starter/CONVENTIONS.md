# CONVENTIONS.md

Use with tools that manually load convention files, especially Aider.

Canonical instructions live in `AGENTS.md`.

## General conventions

- Prefer minimal, reversible changes.
- Preserve public APIs unless the task explicitly requires changing them.
- Add or update tests for behavior changes.
- Do not hide failing tests.
- Do not modify secrets or environment files.
- Explain dependency additions before applying them.

## Aider

```bash
aider --read AGENTS.md --read CONVENTIONS.md
```
