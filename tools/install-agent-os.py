#!/usr/bin/env python3
"""
Install the Conexus Agent OS package into a target directory.

Safe by default:
- Only copies Agent OS governance files, not runtime code
- Requires explicit --overwrite to modify existing files
- --dry-run shows what would be copied without modifying anything
- Skips the installer itself to prevent overwriting

Usage:
    python tools/install-agent-os.py --target /path/to/repo
    python tools/install-agent-os.py --target /path/to/repo --dry-run
    python tools/install-agent-os.py --target /path/to/repo --overwrite
"""

from __future__ import annotations
import argparse
from pathlib import Path

# Files to install (governance layer only, not runtime code)
INSTALL_FILES = [
    'AGENTS.md', 'CLAUDE.md', 'GEMINI.md', 'CONVENTIONS.md', 'QUICKSTART.md',
    '.github/copilot-instructions.md',
    '.aider.conf.yml',
    '.cursor/rules/000-project-rules.mdc',
    '.cursor/rules/010-spdd-workflow.mdc',
    '.windsurf/rules/000-project-rules.md',
    '.windsurf/workflows/implement-from-spec.md',
    '.windsurf/workflows/review-against-scope.md',
    '.continue/rules/00-project-rules.md',
    '.continue/rules/10-spdd.md',
    '.claude/settings.json',
    '.claude/hooks/guard_tool_use.py',
    '.claude/hooks/post_edit_advisor.py',
]

# Directories to install (governance, not runtime)
INSTALL_DIRS = [
    '.agent-os/checklists',
    '.agent-os/examples',
    '.agent-os/manifest.json',
    '.agent-os/policy',
    '.agent-os/snippets',
    '.agent-os/templates',
    'docs/ai',
    'docs/architecture',
    'docs/product',
    'docs/specs',
    'tools/validate-agent-os.py',
    'tools/sync-adapters.py',
]

def should_install(rel_path: str) -> bool:
    """Check if a file/dir should be installed (not runtime code)."""
    # Check exact file matches
    if rel_path in INSTALL_FILES:
        return True
    # Check directory matches
    for d in INSTALL_DIRS:
        if rel_path == d or rel_path.startswith(d + '/'):
            return True
    return False

def main():
    ap = argparse.ArgumentParser(description='Install Conexus Agent OS package')
    ap.add_argument('--target', required=True, help='Target directory for installation')
    ap.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    ap.add_argument('--dry-run', action='store_true', help='Show what would be installed without modifying files')
    a = ap.parse_args()
    
    src = Path(__file__).resolve().parents[1]
    dst = Path(a.target).resolve()
    
    if not a.dry_run:
        dst.mkdir(parents=True, exist_ok=True)
    
    installed = 0
    skipped = 0
    conflicts = 0
    
    # Walk the source directory
    for f in src.rglob('*'):
        if f.is_dir():
            continue
        
        rel = f.relative_to(src)
        rp = rel.as_posix()
        
        # Skip the installer itself
        if rp == 'tools/install-agent-os.py':
            continue
        
        # Only install designated Agent OS files
        if not should_install(rp):
            continue
        
        target = dst / rel
        
        # Check for conflicts
        if target.exists() and not a.overwrite:
            print(f'skip (exists, use --overwrite): {rp}')
            conflicts += 1
            continue
        
        if a.dry_run:
            print(f'would install: {rp}')
            installed += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            txt = f.read_text(encoding='utf-8')
            target.write_text(txt, encoding='utf-8')
            print(f'installed: {rp}')
            installed += 1
    
    # Summary
    print()
    print(f'Summary: {installed} files', end='')
    if conflicts > 0:
        print(f', {conflicts} conflicts (use --overwrite)', end='')
    if a.dry_run:
        print(' (dry-run, no changes made)')
    else:
        print()
    
    if not a.dry_run and installed > 0:
        print()
        print('Next steps:')
        print('1. Review .agent-os/profile.yml for repo-specific differences')
        print('2. Run: python tools/validate-agent-os.py --target .')
        print('3. Commit: git add -A && git commit -m "Install Conexus agent-os"')


if __name__ == '__main__':
    main()
