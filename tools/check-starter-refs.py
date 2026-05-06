#!/usr/bin/env python3
"""
Verify that no docs incorrectly reference docs/spdd-agent-os-starter as canonical.

This script checks that governance and scope docs use root paths, not the starter
package paths, to avoid confusion about which is the canonical source.

Run: python tools/check-starter-refs.py
"""

from __future__ import annotations
import re
from pathlib import Path

# Patterns that suggest docs/spdd-agent-os-starter is treated as canonical
FORBIDDEN_PATTERNS = [
    # Direct references in docs/product, docs/specs, docs/architecture, docs/ai
    r'docs/spdd-agent-os-starter/\.agent-os/profile\.yml',
    r'docs/spdd-agent-os-starter/docs/product',
    r'docs/spdd-agent-os-starter/docs/specs',
    r'docs/spdd-agent-os-starter/docs/architecture',
    r'docs/spdd-agent-os-starter/docs/ai',
    # Instructions that should point to root
    r'docs/spdd-agent-os-starter/AGENTS\.md',
    r'docs/spdd-agent-os-starter/CLAUDE\.md',
    r'docs/spdd-agent-os-starter/GEMINI\.md',
]

# Files to check (governance/scope docs, not runtime docs)
CHECK_PATHS = [
    'docs/product/',
    'docs/specs/',
    'docs/architecture/',
    'docs/ai/',
    'AGENTS.md',
    'CLAUDE.md',
    'GEMINI.md',
    '.github/copilot-instructions.md',
    '.agent-os/profile.yml',
]

# Files/patterns to skip (ok if they reference starter)
SKIP_PATTERNS = [
    'docs/spdd-agent-os-starter/**',  # The starter package itself
    '**/*.backup',
    '**/*.old',
]

def should_check(path: Path) -> bool:
    """Determine if a file should be checked."""
    str_path = path.as_posix()
    
    # Skip if in starter package
    if 'docs/spdd-agent-os-starter' in str_path:
        return False
    
    # Only check docs and instruction files
    for check in CHECK_PATHS:
        if str_path.startswith(check):
            return True
    
    return False

def check_file(path: Path) -> list[tuple[int, str, str]]:
    """Check a file for forbidden references. Returns list of (line_num, pattern, line_text)."""
    issues = []
    try:
        lines = path.read_text(encoding='utf-8').split('\n')
    except (UnicodeDecodeError, IOError):
        return issues
    
    for i, line in enumerate(lines, 1):
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                issues.append((i, pattern, line.strip()))
    
    return issues

def main():
    root = Path('.')
    all_issues = []
    
    print('Checking for incorrect docs/spdd-agent-os-starter references...\n')
    
    for doc_file in root.rglob('*.md'):
        if not should_check(doc_file):
            continue
        
        issues = check_file(doc_file)
        for line_num, pattern, line_text in issues:
            rel_path = doc_file.relative_to(root).as_posix()
            print(f'{rel_path}:{line_num}')
            print(f'  Pattern: {pattern}')
            print(f'  Text: {line_text[:80]}...' if len(line_text) > 80 else f'  Text: {line_text}')
            all_issues.append((rel_path, line_num))
    
    print()
    if all_issues:
        print(f'❌ Found {len(all_issues)} incorrect reference(s)')
        print()
        print('Fix by changing:')
        print('  docs/spdd-agent-os-starter/.agent-os/profile.yml  →  .agent-os/profile.yml')
        print('  docs/spdd-agent-os-starter/docs/product/...  →  docs/product/...')
        print('  docs/spdd-agent-os-starter/docs/specs/...  →  docs/specs/...')
        print('  docs/spdd-agent-os-starter/docs/architecture/...  →  docs/architecture/...')
        print('  docs/spdd-agent-os-starter/docs/ai/...  →  docs/ai/...')
        return 1
    else:
        print('✅ All governance docs use canonical root paths')
        return 0

if __name__ == '__main__':
    exit(main())
