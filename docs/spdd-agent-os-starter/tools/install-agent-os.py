#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', required=True)
    ap.add_argument('--overwrite', action='store_true')
    a = ap.parse_args()
    src = Path(__file__).resolve().parents[1]
    dst = Path(a.target).resolve()
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.rglob('*'):
        if f.is_dir():
            continue
        rel = f.relative_to(src)
        rp = rel.as_posix()
        if rp == 'tools/install-agent-os.py':
            continue
        target = dst / rel
        if target.exists() and not a.overwrite:
            print('skip existing:', rel)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        txt = f.read_text(encoding='utf-8')
        target.write_text(txt, encoding='utf-8')
        print('installed:', rel)
    print('Done. Review .agent-os/profile.yml for repo-specific differences, then validate.')


if __name__ == '__main__':
    main()
