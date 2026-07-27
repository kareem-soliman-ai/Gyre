#!/usr/bin/env python3
"""Catch a reasoning model thinking in circles — in ~6 lines, no API key.

Reasoning models burn thousands of *thinking* tokens per task. Some of that is
rumination: the model circling between two framings ("actually... however...
actually... however...") without taking in new information. Those tokens are pure
cost — nobody even reads them. This demo shows Gyre's L1 loop (a controller) catch
one such loop with a naive, public sensor, and it shows the honest catch: a
consecutive lexical sensor is *fooled* by the rewording, while comparing each
thought against everything thought so far catches the circle.

Run: `python scripts/demo_reasoning_loop.py`  (standard library + this package only)

The six-line version, dropped into your own reasoning/agent loop:

    from gyre import RuminationMonitor, ExitReason
    from gyre.providers import EvidenceNoveltyProvider
    monitor = RuminationMonitor(EvidenceNoveltyProvider(), patience=2, threshold=0.55)
    for thought in thinking_stream:                 # each reasoning step
        monitor.observe(IterationObservation(artifact=thought))
        if monitor.verdict().exit_reason is not ExitReason.CONTINUE:
            break                                   # the loop stopped paying — cut it
"""

from __future__ import annotations

import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from gyre import ExitReason, RuminationMonitor
from gyre.loops.rumination import IterationObservation
from gyre.providers import DiffNoveltyProvider, EvidenceNoveltyProvider

# A reasoning stream (the model's own thinking, no tool calls): a productive
# diagnosis (0-5), then an "actually/however" oscillation that re-derives the same
# trade-off with no new information (6-11). This is where the tokens leak.
THINKING = [
    "Let me work out why the test fails: it expected 12 rows but got 11.",
    "That is an off-by-one in the aggregation, one group is being dropped.",
    "The last group is never flushed after the loop ends, so its row is not appended.",
    "So the minimal fix is to flush the final group once, after the loop.",
    "Actually, maybe I should flush inside the loop when the group key changes, that is cleaner.",
    "However, flushing inside the loop would double-count the last group, since it also flushes after.",
    "Actually, if I only flush after the loop, the intermediate groups are already fine.",
    "However, flushing inside on key-change is the standard pattern and handles every group uniformly.",
    "Actually, the after-loop flush is simpler and I already know it works for the intermediate groups.",
    "However, mixing inside and after flushing risks the double-count I just mentioned.",
    "Actually, let me just flush after the loop, that is the minimal change.",
    "However, is the after-loop flush definitely handling the final key-change correctly...",
]


def _run(provider, *, patience=2, threshold=0.55):
    monitor = RuminationMonitor(provider, patience=patience, threshold=threshold)
    for i, thought in enumerate(THINKING):
        monitor.observe(IterationObservation(artifact=thought, index=i))
        if monitor.verdict().exit_reason is not ExitReason.CONTINUE:
            return i  # the step at which the monitor said "this loop stopped paying"
    return None


def _tokens(segments) -> int:
    return sum(max(1, round(len(s.split()) * 1.3)) for s in segments)


def main() -> int:
    total = _tokens(THINKING)
    print("A reasoning model, thinking:\n")
    for i, t in enumerate(THINKING):
        marker = "  <- starts circling here" if i == 6 else ""
        print(f"  [{i:>2}] {t}{marker}")

    print("\n--- Sensor A: consecutive lexical novelty (naive:diff-novelty) ---")
    fooled = _run(DiffNoveltyProvider())
    if fooled is None:
        print("  never fired: FOOLED. Each 'actually/however' is reworded, so step-to-step")
        print("  it always looks novel. Lexical novelty cannot see a semantic circle.")
    else:
        print(f"  fired at step {fooled}")

    print("\n--- Sensor B: novelty vs ALL prior thinking (naive:evidence-novelty) ---")
    caught = _run(EvidenceNoveltyProvider())
    if caught is not None:
        saved = _tokens(THINKING[caught:])
        print(f"  fired at step {caught} — the moment the thinking stopped adding information.")
        print(f"  Stopping here saves ~{saved} of ~{total} thinking tokens on this toy trace")
        print(f"  ({saved / total:.0%}). In a real reasoning model these loops run for")
        print("  hundreds to thousands of tokens — pure cost, and nobody reads them.")
    else:
        print("  never fired.")

    print("\nThe point: which way is healthy is not the question — WHETHER each step adds")
    print("information is. Naive sensors are crude proxies (this one only compares text).")
    print("Bring your own sensor and score it head-to-head: `from gyre.bench import compare_providers`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
