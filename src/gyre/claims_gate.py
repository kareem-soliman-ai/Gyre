"""Claims-integrity gate: a public claim cannot outlive its evidence.

Adapted from an earlier science-bundle gate that forced public claims to be
withdrawn when their evidence changed. Gyre's version
binds the repo's headline numbers — the sensor ladder, the regret table, the
demo savings — to a machine-checked ledger:

- Every public claim carries an inline tag ``<!-- claim:GYR-NN -->`` bound to a
  ledger entry with a status (``confirmed`` / ``provisional`` / ``contested`` /
  ``cannot-claim``) and its evidence pointer.
- The gate FAILS on: dangling tags (no ledger entry), tags whose entry is not
  publicly assertable (``cannot-claim``/``contested`` or ``public_allowed``
  false), and forbidden phrases appearing on untagged lines (the safety net for
  numbers pasted without a tag).
- ``provisional`` claims must sit near a caveat marker on the same line; a miss
  is a WARNING (ship, but fix the copy).

Run via ``scripts/check_claims.py`` (CI-friendly: exit 1 on failure). The
ledger is the single source of citable figures: update the ledger when an eval
re-run moves a number, and the gate turns the stale doc red.

Dependencies: standard library only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TAG_RE = re.compile(r"claim:([A-Z]+-\d+)")

_PUBLIC_STATUSES = ("confirmed", "provisional")
_DEFAULT_CAVEATS = ("synthetic", "simulator", "simulated", "preliminary", "demo", "provisional")


@dataclass
class ClaimCheckResult:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def load_ledger(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_claims(doc_texts: dict[str, str], ledger: dict[str, Any]) -> ClaimCheckResult:
    """Check public doc texts against the claims ledger.

    ``doc_texts`` maps a display name (path) to the document's full text.
    Returns failures (gate red) and warnings (gate green, copy needs care).
    """
    claims: dict[str, Any] = ledger.get("claims", {})
    forbidden: list[str] = ledger.get("forbidden_phrases", [])
    result = ClaimCheckResult()

    for doc, text in doc_texts.items():
        for lineno, line in enumerate(text.splitlines(), start=1):
            tags = TAG_RE.findall(line)
            low = line.lower()

            for tag in tags:
                entry = claims.get(tag)
                if entry is None:
                    result.failures.append(
                        f"{doc}:{lineno}: dangling tag claim:{tag} — no ledger entry"
                    )
                    continue
                status = entry.get("status", "cannot-claim")
                if status not in _PUBLIC_STATUSES or not entry.get("public_allowed", False):
                    result.failures.append(
                        f"{doc}:{lineno}: claim:{tag} has status {status!r} "
                        f"(public_allowed={entry.get('public_allowed', False)}) — "
                        "not publicly assertable"
                    )
                    continue
                if status == "provisional":
                    markers = [
                        m.lower()
                        for m in entry.get("caveat_markers", _DEFAULT_CAVEATS)
                    ]
                    if not any(m in low for m in markers):
                        result.warnings.append(
                            f"{doc}:{lineno}: provisional claim:{tag} has no nearby "
                            f"caveat (wanted one of: {', '.join(markers)})"
                        )

            if not tags:
                for phrase in forbidden:
                    if phrase.lower() in low:
                        result.failures.append(
                            f"{doc}:{lineno}: forbidden phrase {phrase!r} on an "
                            "untagged line — tag it to a ledger claim or remove it"
                        )
    return result


def check_files(paths: list[Path], ledger_path: Path) -> ClaimCheckResult:
    """Convenience wrapper: read files and check them against a ledger file."""
    ledger = load_ledger(ledger_path)
    docs = {
        str(p): p.read_text(encoding="utf-8", errors="replace")
        for p in paths
        if p.is_file()
    }
    return check_claims(docs, ledger)
