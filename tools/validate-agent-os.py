#!/usr/bin/env python3
"""
Validate Conexus Agent OS package installation.

Checks that all required Agent OS governance files exist and are valid.
"""

from __future__ import annotations
import argparse, json
from pathlib import Path

# Core Agent OS files (must exist)
REQUIRED = [
    'AGENTS.md',
    'CLAUDE.md',
    'GEMINI.md',
    'CONVENTIONS.md',
    '.agent-os/profile.yml',
    '.github/copilot-instructions.md',
    '.cursor/rules/000-project-rules.mdc',
    '.windsurf/rules/000-project-rules.md',
    '.continue/rules/00-project-rules.md',
]

# Optional Claude support files (if .claude exists, these should be present)
OPTIONAL_CLAUDE = [
    '.claude/settings.json',
    '.claude/hooks/guard_tool_use.py',
]

def main():
    ap = argparse.ArgumentParser(description='Validate Conexus Agent OS installation')
    ap.add_argument('--target', default='.', help='Target directory to validate')
    a = ap.parse_args()
    
    root = Path(a.target).resolve()
    
    # Check required files
    missing = [x for x in REQUIRED if not (root / x).exists()]
    if missing:
        print('Missing required files:')
        for m in missing:
            print(f'  - {m}')
        raise SystemExit(1)
    
    # Check .claude/settings.json is valid JSON if present
    claude_settings = root / '.claude/settings.json'
    if claude_settings.exists():
        try:
            json.loads(claude_settings.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError) as e:
            print(f'Invalid .claude/settings.json: {e}')
            raise SystemExit(1)
        
        # If .claude exists, check optional files
        missing_claude = [x for x in OPTIONAL_CLAUDE if not (root / x).exists()]
        if missing_claude:
            print('Warning: .claude/settings.json exists but missing optional files:')
            for m in missing_claude:
                print(f'  - {m}')
    
    print('SPDD Agent OS validation passed:', root)


if __name__ == '__main__':
    main()
