# Quickstart

1. Install into a repo:

```bash
python tools/install-agent-os.py --target ../my-repo
```

2. Edit `.agent-os/profile.yml`.

3. Validate:

```bash
python ../my-repo/tools/validate-agent-os.py --target ../my-repo
```

4. Start any coding agent with:

```text
Read AGENTS.md and .agent-os/profile.yml. Work in PLAN mode first. Summarize the smallest safe Conexus vertical slice before editing files.
```

5. Use explicit modes: ASK, PLAN, IMPLEMENT, REVIEW, DEBUG, DOCUMENT, RESCUE.
