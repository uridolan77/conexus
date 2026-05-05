# 03 — Ontogony CMS Schema Reference

Use the actual Ontogony site schema as the formatter contract.

Relevant repo:

```text
uridolan77/ontogony-site
```

Relevant files:

```text
tina/config.ts
src/content.config.ts
```

## Collections

Astro/Tina content collections include:

```text
concepts
essays
paths
diagrams
fragments
quizzes
flashcards
```

For Agentor v0.1, support only:

```text
essay
concept
fragment
```

Default to `essay`.

## Essay frontmatter

Target directory:

```text
src/content/essays/{slug}.mdx
```

Minimum valid frontmatter:

```yaml
---
title: "..."
summary: "..."
status: "draft"
date: "2026-05-05T00:00:00.000Z"
register: "R2"
readingTime: 8
cites: []
featuredDiagram:
relatedDiagrams: []
whereNext: []
createdAt: "2026-05-05T00:00:00.000Z"
updatedAt: "2026-05-05T00:00:00.000Z"
---
```

For generated content, always use:

```text
status: draft
```

## Concept frontmatter

Target directory:

```text
src/content/concepts/{slug}.mdx
```

Minimum valid frontmatter:

```yaml
---
title: "..."
short: "..."
register: "R2"
related: []
featuredDiagram:
relatedDiagrams: []
genealogy: []
notThis: []
whereNext: []
status: "draft"
createdAt: "..."
updatedAt: "..."
---
```

## Fragment frontmatter

Target directory:

```text
src/content/fragments/{slug}.mdx
```

Minimum valid frontmatter:

```yaml
---
title: "..."
chapterNumber:
bookTitle:
status: "draft"
createdAt: "..."
updatedAt: "..."
---
```

## Formatting requirement

Do not hand-build YAML with unsafe string interpolation.

Prefer:

```python
yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
```

Add tests for quotes, colons, newlines, unicode, empty arrays, and null optional fields.
