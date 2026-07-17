#!/usr/bin/env python3
"""Absorb human labels from the scoring worksheet back into the scoring set JSON.

Run this after you've marked up the worksheet by adding ``[x]`` to rumination steps:

    python scripts/absorb_worksheet.py

This reads the worksheet markdown, parses the checked boxes, and updates the
corresponding entries in ``scoring_set.json``. It preserves all existing labels
so you can run it incrementally.

Usage:
    python scripts/absorb_worksheet.py
    python scripts/absorb_worksheet.py --worksheet traces/private/scoring_worksheet.md --scoring-set traces/private/scoring_set.json
    python scripts/absorb_worksheet.py --dry-run  # preview changes without writing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_worksheet(path: Path) -> dict[str, dict[int, tuple[bool, str]]]:
    """Parse the worksheet markdown and return
    {trace_id: {step_index: (is_ruminating, rationale)}}.

    The worksheet format is::

        ## trace_id
        **[0]** step text ...
        - rumination? [x] rationale: ...

    Where ``[x]`` means ruminating and ``[ ]`` means not ruminating. Rationale
    text after ``rationale:`` is captured too — it rides into the scoring set,
    where it becomes evidence when qualifying a judge against these labels.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    result: dict[str, dict[int, tuple[bool, str]]] = {}
    current_trace: str | None = None
    current_idx: int | None = None

    # Pattern: ## trace_id  (the section header)
    trace_header = re.compile(r"^##\s+(\S+)")
    # Pattern: **[N]**  (step index)
    step_idx = re.compile(r"^\*\*\[(\d+)\]\*\*")
    # Pattern: - rumination? [x] rationale: <text>  (the checkbox line)
    checkbox = re.compile(r"- rumination\?\s+\[(x|X| )\]\s+rationale:\s*(.*)$")

    for line in lines:
        m = trace_header.match(line)
        if m:
            current_trace = m.group(1)
            current_idx = None
            if current_trace not in result:
                result[current_trace] = {}
            continue

        m = step_idx.match(line)
        if m and current_trace:
            current_idx = int(m.group(1))
            result[current_trace].setdefault(current_idx, (False, ""))
            continue

        m = checkbox.match(line)
        if m and current_trace and current_idx is not None:
            checked = m.group(1) not in (" ", "")
            result[current_trace][current_idx] = (checked, m.group(2).strip())

    return result


def absorb(
    scoring_set_path: Path,
    labels: dict[str, dict[int, tuple[bool, str]]],
    *,
    dry_run: bool = False,
) -> int:
    """Update scoring_set.json with parsed labels. Returns number of changes."""
    scoring_set = json.loads(scoring_set_path.read_text(encoding="utf-8"))

    changes = 0
    for trace_entry in scoring_set:
        trace_id = trace_entry.get("trace_id", "")
        trace_labels = labels.get(trace_id, {})
        if not trace_labels:
            continue

        steps = trace_entry.get("steps", [])
        for step in steps:
            idx = step.get("index", -1)
            if idx in trace_labels:
                new_val, rationale = trace_labels[idx]
                changed = step.get("is_ruminating", False) != new_val or (
                    rationale and step.get("rationale", "") != rationale
                )
                if changed:
                    step["is_ruminating"] = new_val
                    if rationale:
                        step["rationale"] = rationale
                    step["scorer"] = "human"
                    changes += 1

    if dry_run:
        print(f"[DRY-RUN] Would update {changes} labels in {scoring_set_path}")
    else:
        with open(scoring_set_path, "w", encoding="utf-8") as fh:
            json.dump(scoring_set, fh, indent=2, ensure_ascii=False)
        print(f"[OK] Updated {changes} labels in {scoring_set_path}")

    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Absorb worksheet labels into the scoring set.")
    ap.add_argument("--worksheet", default="traces/private/scoring_worksheet.md")
    ap.add_argument("--scoring-set", default="traces/private/scoring_set.json")
    ap.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = ap.parse_args()

    ws_path = Path(args.worksheet)
    ss_path = Path(args.scoring_set)

    if not ws_path.exists():
        print(f"[ERROR] Worksheet not found: {ws_path}")
        return 1
    if not ss_path.exists():
        print(f"[ERROR] Scoring set not found: {ss_path}")
        return 1

    labels = parse_worksheet(ws_path)
    total_checked = sum(
        1 for trace_labels in labels.values() for v, _ in trace_labels.values() if v
    )
    print(f"[INFO] Parsed {len(labels)} traces from worksheet ({total_checked} steps marked ruminating)")
    absorb(ss_path, labels, dry_run=args.dry_run)
    if total_checked == 0 and not args.dry_run:
        print("[WARN] No steps are marked ruminating. If you have scored the worksheet")
        print("       and genuinely found none, fine; if not, tick [x] boxes first —")
        print("       downstream tools treat an all-negative set as an unscored template.")
    else:
        print("[NEXT] python scripts/qualify_judges.py   (qualify an LLM judge against your labels)")
    return 0


if __name__ == "__main__":
    sys.exit(main())