#!/usr/bin/env python3
from pathlib import Path
ADAPTERS={
 'CLAUDE.md':'# Claude Code Instructions\n\nRead `AGENTS.md` first. It is the canonical instruction file for this repository.\n',
 'GEMINI.md':'# Gemini CLI Instructions\n\nRead `AGENTS.md` first. It is the canonical instruction file for this repository.\n',
 '.github/copilot-instructions.md':'# GitHub Copilot Repository Instructions\n\nUse `AGENTS.md` as the canonical repository guidance.\n'
}
for rel,txt in ADAPTERS.items():
    p=Path(rel); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt,encoding='utf-8'); print('wrote',rel)
