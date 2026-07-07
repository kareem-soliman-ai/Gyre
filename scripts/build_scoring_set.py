"""Build a small, human-scoreable rumination set from real Claude Code transcripts.

For each transcript it ingests the assistant turns (text + tool actions), finds the
window with the densest repetition of tool targets (where a retry/stuck episode is
most likely), and emits that window as a ScoredTrace template with is_ruminating
defaulted to False. You flip the booleans and add a one-line rationale; that
becomes your human gold set for judge qualification.

Output goes to traces/private/ (gitignored): the JSON template the pipeline loads,
plus a readable Markdown worksheet to score against.

Usage:
    python scripts/build_scoring_set.py <transcript.jsonl> [more ...] \
        --window 12 --out-dir traces/private
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gyre.traces import RawTrace, ScoredStep, ScoredTrace, from_claude_code_jsonl, save_traces


# Tools where repeating the SAME target is a genuine retry/rumination signal.
# Batch operations (completing many tasks, reading many files) repeat a tool but
# not a target, and are productive, not ruminative. That distinction is the whole
# point of the project, so the candidate-finder has to respect it.
_RETRY_PRONE = ("Edit", "Write", "MultiEdit", "NotebookEdit", "Bash")


def _primary_target(step) -> str | None:
    """The retry-relevant target of a step: an Edit/Write/Bash action with its
    actual file/command. Returns None for batch tools, so re-editing the same file
    counts as a repeat but completing seven different tasks does not."""
    for action in step.meta.get("actions") or []:
        head, _, rest = action.partition(":")
        if head.strip() in _RETRY_PRONE and rest.strip():
            # Compare on tool+file only; the change snippet after " -> " is shown to
            # the scorer but must not split a same-file retry cluster.
            return action.split(" -> ")[0]
    return None


def densest_window(trace: RawTrace, size: int) -> tuple[int, int]:
    """Return (start, end) of the window of `size` steps with the most consecutive
    repeated tool targets. Falls back to the middle of the trace if no actions."""
    n = len(trace.steps)
    if n <= size:
        return 0, n
    repeats = [0] * n
    for i in range(1, n):
        a, b = _primary_target(trace.steps[i]), _primary_target(trace.steps[i - 1])
        repeats[i] = 1 if (a is not None and a == b) else 0
    best_start, best_score = 0, -1
    for start in range(0, n - size + 1):
        score = sum(repeats[start : start + size])
        if score > best_score:
            best_score, best_start = score, start
    if best_score <= 0:  # no repetition anywhere: take the middle
        best_start = max(0, (n - size) // 2)
    return best_start, best_start + size


def to_template(trace: RawTrace, start: int, end: int, text_cap: int = 2000) -> ScoredTrace:
    steps = []
    for i, step in enumerate(trace.steps[start:end]):
        steps.append(
            ScoredStep(
                text=step.text[:text_cap],
                is_ruminating=False,  # <-- you flip these
                index=i,
                rationale="",         # <-- one sentence why
                scorer="human",
            )
        )
    return ScoredTrace(steps=steps, source=trace.source, trace_id=f"{trace.trace_id}[{start}:{end}]")


def worksheet_md(templates: list[ScoredTrace], step_cap: int = 500) -> str:
    lines = [
        "# Rumination scoring worksheet",
        "",
        "For each step, decide: does it add new information relative to the steps",
        "before it (reflection) or recycle old ground (rumination)? See",
        "docs/rumination-rubric.md. Mark rumination steps by setting `is_ruminating`",
        "to `true` in the matching JSON, and jot a one-line rationale.",
        "",
    ]
    for st in templates:
        lines.append(f"## {st.trace_id}")
        lines.append(f"_source: {st.source}_")
        lines.append("")
        for s in st.steps:
            snippet = " ".join(s.text.split())[:step_cap]
            lines.append(f"**[{s.index}]** {snippet}")
            lines.append("")
            lines.append("- rumination? [ ]   rationale: ")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a scoreable rumination set from transcripts.")
    ap.add_argument("inputs", nargs="+", help="Claude Code .jsonl transcripts")
    ap.add_argument("--window", type=int, default=12, help="steps per scoring window")
    ap.add_argument("--out-dir", default="traces/private", help="output dir (gitignored)")
    ap.add_argument("--no-thinking", action="store_true", help="exclude agent thinking blocks")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    templates: list[ScoredTrace] = []
    for path in args.inputs:
        trace = from_claude_code_jsonl(path, include_thinking=not args.no_thinking)
        if len(trace.steps) < 4:
            print(f"  {Path(path).name}: only {len(trace.steps)} steps, skipping")
            continue
        start, end = densest_window(trace, args.window)
        repeat_count = sum(
            1 for i in range(start + 1, end)
            if _primary_target(trace.steps[i]) and _primary_target(trace.steps[i]) == _primary_target(trace.steps[i - 1])
        )
        templates.append(to_template(trace, start, end))
        print(f"  {Path(path).name}: {len(trace.steps)} steps -> window [{start}:{end}], "
              f"{repeat_count} repeated-target steps")

    json_path = out / "scoring_set.json"
    md_path = out / "scoring_worksheet.md"
    save_traces(templates, json_path)
    md_path.write_text(worksheet_md(templates), encoding="utf-8")

    total = sum(len(t.steps) for t in templates)
    print(f"\nWrote {len(templates)} traces ({total} steps) to score:")
    print(f"  template (edit booleans): {json_path}")
    print(f"  readable worksheet:       {md_path}")
    print("\nNext: score the steps, then qualify a judge with scripts/qualify_judges.py")


if __name__ == "__main__":
    main()
