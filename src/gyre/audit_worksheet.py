"""Blinded expert-audit worksheet: the cheapest hour that unblocks a claim.

Two different questions need an expert, and they are usually confused:

- **Anchor** — adjudicate the steps the panel genuinely split on. This is what
  qualifies the judges against labels they did not set.
- **Audit** — re-check a RANDOM SAMPLE OF AUTO-APPROVED steps, to bound what
  the panel waved through. This is the number nobody measures, and without it
  a burden-reduction figure is unclaimable (see ``gyre.verification_audit``).

Both are collected in one pass here, and the expert is not told which is which.
That matters: knowing an item was "the hard one" changes how hard you look, and
knowing an item was auto-approved invites rubber-stamping. So the worksheet
leaks nothing — no labels, no probabilities, no provenance, and the two kinds
are interleaved. The absorber matches ticks back to the hidden labels
afterwards.

The sample size is the claim strength: 35 audited auto-approved items with zero
escapes supports a 10% escape ceiling, 73 supports 5%
(``verification_audit.audit_sample_size_for``). Not the corpus size — the audit
size.

Dependencies: standard library only.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from gyre.verification_audit import EscapeBound, escape_rate_bound

_TICK = re.compile(r"^\s*\[([xX ])\]\s*(ruminating|productive)\s*$")
_ITEM = re.compile(r"^##\s+(ITEM-\d+)\s*$")


@dataclass
class AuditItem:
    item_id: str
    trace_id: str
    index: int
    text: str
    context: tuple[str, ...]
    kind: str            # "audit" (auto-approved) | "anchor" (panel-disputed)
    hidden_label: bool | None   # the panel's call; NEVER rendered


@dataclass
class AbsorbResult:
    expert_labels: dict[str, bool] = field(default_factory=dict)
    n_marked: int = 0
    audited: int = 0
    escapes: int = 0
    anchors: dict[str, bool] = field(default_factory=dict)
    conflicts: tuple[str, ...] = ()
    bound: EscapeBound | None = None

    def summary(self) -> str:
        if self.conflicts:
            return f"{len(self.conflicts)} item(s) ticked both ways: {', '.join(self.conflicts)}"
        if not self.n_marked:
            return "nothing marked yet"
        parts = [
            f"{self.n_marked} items marked",
            f"{self.audited} auto-approved audited, {self.escapes} escape(s)",
            f"{len(self.anchors)} expert anchors collected",
        ]
        if self.bound:
            parts.append(self.bound.note)
        return "; ".join(parts)


def sample_audit_items(
    records: Sequence[dict[str, Any]],
    *,
    n_auto: int,
    seed: int = 20260727,
    context_steps: int = 3,
) -> list[AuditItem]:
    """Draw a blinded worksheet sample: ``n_auto`` random auto-approved steps
    plus EVERY panel-disputed step, interleaved."""
    auto: list[tuple[str, dict]] = []
    disputed: list[tuple[str, dict]] = []
    text_by_trace: dict[str, list[dict]] = {}
    for rec in records:
        text_by_trace[rec["trace_id"]] = rec["steps"]
        for s in rec["steps"]:
            prov = s.get("provenance")
            if prov in ("auto", "auto_majority") and s.get("is_ruminating") is not None:
                auto.append((rec["trace_id"], s))
            elif prov == "human_needed":
                disputed.append((rec["trace_id"], s))

    if n_auto > len(auto):
        raise ValueError(
            f"asked for {n_auto} auto-approved items but only {len(auto)} exist"
        )
    rng = random.Random(seed)
    picked_auto = rng.sample(auto, n_auto)

    def build(pairs, kind) -> list[AuditItem]:
        out = []
        for tid, s in pairs:
            prior = [
                p["text"] for p in text_by_trace[tid] if p["index"] < s["index"]
            ][-context_steps:]
            out.append(
                AuditItem(
                    item_id="",
                    trace_id=tid,
                    index=s["index"],
                    text=s["text"],
                    context=tuple(prior),
                    kind=kind,
                    hidden_label=s.get("is_ruminating"),
                )
            )
        return out

    items = build(picked_auto, "audit") + build(disputed, "anchor")
    rng.shuffle(items)  # kind must not be guessable from position
    for n, item in enumerate(items, start=1):
        item.item_id = f"ITEM-{n:03d}"
    return items


def render_worksheet(items: Sequence[AuditItem], *, title: str = "Gyre expert audit") -> str:
    """Render the blinded worksheet. Leaks no panel verdict, by construction:
    only the step text and its immediate context are written out."""
    lines = [
        f"# {title}",
        "",
        "Tick ONE box per item. Judge each step on its own merits: in the context",
        "of the steps before it, did this step add new information (productive), or",
        "did it recycle what was already known (ruminating)?",
        "",
        "You are NOT being shown any machine verdict. Some of these were easy for",
        "the panel and some were contested; you cannot tell which, and that is the",
        "point - your marks have to be independent to be worth anything.",
        "",
        "Leave an item blank if you genuinely cannot tell. Blank is a real answer",
        "here (it is excluded, not guessed).",
        "",
        "---",
        "",
    ]
    for item in items:
        lines.append(f"## {item.item_id}")
        if item.context:
            lines.append("")
            lines.append("Preceding steps:")
            for c in item.context:
                lines.append(f"  | {' '.join(c.split())[:300]}")
        lines.append("")
        lines.append("THIS STEP:")
        for line in item.text.splitlines():
            lines.append(f"  > {line[:300]}")
        lines.append("")
        lines.append("[ ] ruminating")
        lines.append("[ ] productive")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def items_to_json(items: Sequence[AuditItem]) -> list[dict[str, Any]]:
    """Serialise the item->hidden-label key. Plain JSON on purpose: the key is
    read back by the absorber, so it must be inspectable and must not be able to
    execute anything on load."""
    return [
        {
            "item_id": i.item_id,
            "trace_id": i.trace_id,
            "index": i.index,
            "text": i.text,
            "context": list(i.context),
            "kind": i.kind,
            "hidden_label": i.hidden_label,
        }
        for i in items
    ]


def items_from_json(data: Sequence[dict[str, Any]]) -> list[AuditItem]:
    return [
        AuditItem(
            item_id=d["item_id"],
            trace_id=d["trace_id"],
            index=d["index"],
            text=d["text"],
            context=tuple(d.get("context", ())),
            kind=d["kind"],
            hidden_label=d.get("hidden_label"),
        )
        for d in data
    ]


def absorb_worksheet(
    text: str,
    items: Sequence[AuditItem],
    *,
    marks: dict[str, bool] | None = None,
) -> AbsorbResult:
    """Read ticked boxes back and compute the escape bound.

    ``marks`` overrides parsing (used by callers holding structured input).
    Items ticked both ways are reported as conflicts and nothing is absorbed
    until they are resolved — a contradictory mark must never be silently
    resolved in either direction."""
    by_id = {i.item_id: i for i in items}
    parsed: dict[str, bool] = {}
    conflicts: list[str] = []

    if marks is None:
        current: str | None = None
        ticks: dict[str, list[str]] = {}
        for line in text.splitlines():
            m = _ITEM.match(line)
            if m:
                current = m.group(1)
                continue
            t = _TICK.match(line)
            if t and current and t.group(1).lower() == "x":
                ticks.setdefault(current, []).append(t.group(2))
        for item_id, chosen in ticks.items():
            if len(set(chosen)) > 1:
                conflicts.append(item_id)
            else:
                parsed[item_id] = chosen[0] == "ruminating"
    else:
        parsed = dict(marks)

    if conflicts:
        return AbsorbResult(conflicts=tuple(sorted(conflicts)))

    audited = escapes = 0
    anchors: dict[str, bool] = {}
    for item_id, expert in parsed.items():
        item = by_id.get(item_id)
        if item is None:
            continue
        if item.kind == "audit":
            audited += 1
            if item.hidden_label is not None and expert != item.hidden_label:
                escapes += 1
        else:
            anchors[item_id] = expert

    return AbsorbResult(
        expert_labels=parsed,
        n_marked=len(parsed),
        audited=audited,
        escapes=escapes,
        anchors=anchors,
        bound=escape_rate_bound(audited=audited, escapes=escapes),
    )
