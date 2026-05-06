# Hook Policy

Included Claude hooks:

- `.claude/hooks/guard_tool_use.py`
- `.claude/hooks/post_edit_advisor.py`

`guard_tool_use.py` blocks destructive shell commands, direct secret-file access, force push / hard reset / git clean, and protected governance/spec writes unless bypassed.

Bypass intentional protected edits:

```bash
export ALLOW_AGENT_OS_PROTECTED_EDIT=1
```

PowerShell:

```powershell
$env:ALLOW_AGENT_OS_PROTECTED_EDIT = "1"
```

These hooks are Conexus guardrails, not a full security boundary. Keep CI, reviews, branch protections, migration review, and secret scanning in place.
