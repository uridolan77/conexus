#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
REQ=['AGENTS.md','CLAUDE.md','GEMINI.md','CONVENTIONS.md','.agent-os/profile.yml','.github/copilot-instructions.md','.cursor/rules/000-project-rules.mdc','.windsurf/rules/000-project-rules.md','.continue/rules/00-project-rules.md','.claude/settings.json','.claude/hooks/guard_tool_use.py']
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--target',default='.'); a=ap.parse_args(); root=Path(a.target).resolve()
    miss=[x for x in REQ if not (root/x).exists()]
    if miss:
        print('Missing files:'); [print('- '+m) for m in miss]; raise SystemExit(1)
    json.loads((root/'.claude/settings.json').read_text(encoding='utf-8'))
    print('SPDD Agent OS validation passed:', root)
if __name__=='__main__': main()
