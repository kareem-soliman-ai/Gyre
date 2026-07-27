#!/usr/bin/env python3
"""Generate the blinded expert-audit worksheet, and absorb it once marked.

    python scripts/make_audit_worksheet.py --n-auto 35      # generate
    python scripts/make_audit_worksheet.py --absorb         # read the marks back

The sample size sets the claim: 35 audited auto-approved steps with zero escapes
supports a 10% escape ceiling, 73 supports 5%. Every panel-disputed step is
included regardless, because those are the expert anchors that qualify the
judges non-circularly.

The worksheet shows no machine verdict of any kind. The item->label mapping is
written to a separate key file that you should not open until after marking.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))

from gyre.audit_worksheet import (  # noqa: E402
    absorb_worksheet,
    items_from_json,
    items_to_json,
    render_worksheet,
    sample_audit_items,
)
from gyre.verification_audit import AuditResult  # noqa: E402

DEFAULT_LABELS = "traces/private/panel_labels.json"
SHEET = _root / "traces" / "private" / "audit_worksheet.md"
KEY = _root / "traces" / "private" / "audit_worksheet_key.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-auto", type=int, default=35)
    ap.add_argument("--seed", type=int, default=20260727)
    ap.add_argument("--absorb", action="store_true")
    ap.add_argument("--ceiling", type=float, default=0.10)
    ap.add_argument(
        "--labels",
        default=DEFAULT_LABELS,
        help="panel-label JSON to audit (your own corpus; kept out of git)",
    )
    args = ap.parse_args()

    labels_path = _root / args.labels

    if args.absorb:
        if not KEY.exists():
            print(f"[ERROR] no key at {KEY}; generate the worksheet first", file=sys.stderr)
            return 1
        items = items_from_json(json.loads(KEY.read_text(encoding='utf-8')))
        result = absorb_worksheet(SHEET.read_text(encoding="utf-8"), items)
        print(result.summary())
        if result.conflicts:
            return 1
        if not result.n_marked:
            print("nothing marked yet — tick the boxes in", SHEET)
            return 1

        total_steps = sum(
            len(r["steps"]) for r in json.loads(labels_path.read_text(encoding="utf-8"))
        )
        human = len(result.anchors)
        audit = AuditResult.build(
            total=total_steps,
            human_reviewed=human,
            audited=result.audited,
            escapes=result.escapes,
            ceiling=args.ceiling,
        )
        print()
        print(audit.summary())
        out = _root / "internal" / "results" / "expert-audit.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "audited": result.audited,
                    "escapes": result.escapes,
                    "escape_upper": audit.escape.upper,
                    "burden_reduction": audit.burden_reduction,
                    "promotable": audit.promotable,
                    "blocking_reason": audit.blocking_reason,
                    "anchors": result.anchors,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote {out}")
        return 0

    records = json.loads(labels_path.read_text(encoding="utf-8"))
    items = sample_audit_items(records, n_auto=args.n_auto, seed=args.seed)
    SHEET.write_text(render_worksheet(items), encoding="utf-8")
    KEY.write_text(json.dumps(items_to_json(items), indent=2), encoding='utf-8')
    n_anchor = sum(1 for i in items if i.kind == "anchor")
    print(f"wrote {SHEET}")
    print(
        f"  {len(items)} items: {args.n_auto} blinded audit + {n_anchor} expert anchors, "
        f"interleaved and unlabelled"
    )
    print(f"  key (do not open until marked): {KEY}")
    print(f"\nWhen done:  python {Path(__file__).name} --absorb")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
