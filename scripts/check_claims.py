#!/usr/bin/env python3
"""Claims-integrity gate: fail if a public doc asserts more than the ledger allows.

Scans the public docs (README.md, docs/*.md, loops/*.md by default) for claim
tags and forbidden phrases, checks them against docs/claims-ledger.json, and
exits non-zero on any failure — CI-friendly. See gyre.claims_gate for the rules.

Usage:
    python scripts/check_claims.py
    python scripts/check_claims.py --ledger docs/claims-ledger.json README.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre.claims_gate import check_files  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def default_docs() -> list[Path]:
    docs = [REPO / "README.md"]
    docs += sorted((REPO / "docs").glob("*.md"))
    docs += sorted((REPO / "loops").glob("*.md"))
    return [p for p in docs if p.is_file()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="docs to scan (default: README, docs/, loops/)")
    ap.add_argument("--ledger", default=str(REPO / "docs" / "claims-ledger.json"))
    args = ap.parse_args()

    paths = [Path(f) for f in args.files] if args.files else default_docs()
    result = check_files(paths, Path(args.ledger))

    for w in result.warnings:
        print(f"WARN  {w}")
    for f in result.failures:
        print(f"FAIL  {f}")
    if result.ok:
        print(f"claims gate: OK ({len(paths)} docs, {len(result.warnings)} warnings)")
        return 0
    print(f"claims gate: {len(result.failures)} failure(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
