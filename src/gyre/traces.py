"""Trace ingestion and the labelled-corpus format.

The evaluation needs a corpus of real agent behaviour with ground-truth labels:
which steps were part of a ruminative episode and which were productive. This
module handles getting raw traces in (from a Claude Code transcript, a mem0 log,
or anything you can turn into ordered text steps) and holding the labelled result
in a stable shape that the judge pipeline and the benchmark both understand.

The format is deliberately source-agnostic. A ``RawTrace`` is just ordered text
steps; where they came from does not matter. A ``ScoredTrace`` adds a per-step
label and rationale. ``ScoredTrace.to_bench`` converts to the
``gyre.bench.LabelledTrace`` the benchmark scores providers against, so labelling
a corpus once feeds both the judge-qualification check and the sensor comparison.

Dependencies: standard library only.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class TraceStep:
    """One ordered step of agent output. The unit a rumination judge scores."""

    text: str
    role: str = "assistant"
    index: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawTrace:
    """An ordered sequence of steps from one agent episode, unlabelled."""

    steps: list[TraceStep]
    source: str = ""
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "source": self.source,
            "steps": [asdict(s) for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RawTrace":
        return cls(
            steps=[TraceStep(**s) for s in d.get("steps", [])],
            source=d.get("source", ""),
            trace_id=d.get("trace_id", ""),
        )


@dataclass
class ScoredStep:
    """A step with a ground-truth (or judge) label and the reason for it."""

    text: str
    is_ruminating: bool
    index: int = 0
    rationale: str = ""
    scorer: str = ""


@dataclass
class ScoredTrace:
    """A trace whose steps carry rumination labels. The corpus unit."""

    steps: list[ScoredStep]
    source: str = ""
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "source": self.source,
            "steps": [asdict(s) for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ScoredTrace":
        return cls(
            steps=[ScoredStep(**s) for s in d.get("steps", [])],
            source=d.get("source", ""),
            trace_id=d.get("trace_id", ""),
        )

    def labels(self) -> list[bool]:
        return [s.is_ruminating for s in self.steps]

    def to_bench(self, loop_id: str = "L1"):
        """Convert to a ``gyre.bench.LabelledTrace`` for scoring providers.

        Each step becomes an ``IterationObservation`` (the L1 observation shape),
        so a rumination sensor can be scored against this corpus directly.
        """
        from gyre.bench import LabelledTrace
        from gyre.loops.rumination import IterationObservation

        observations = [
            IterationObservation(artifact=s.text, index=s.index) for s in self.steps
        ]
        return LabelledTrace(
            observations=observations,
            labels=self.labels(),
            loop_id=loop_id,
            name=self.trace_id or "trace",
        )


# --- ingestion -----------------------------------------------------------------

def _extract_text(record: dict[str, Any]) -> str | None:
    """Best-effort pull of assistant text from one transcript record.

    Transcript formats vary (Claude Code, mem0 exports, custom logs). Rather than
    bind to one, dig for the common shapes: a ``message`` with ``content`` that is
    a string or a list of ``{"type":"text","text":...}`` blocks, or a top-level
    ``text``/``content`` string. Returns None if the record is not assistant text.
    """
    role = record.get("role") or record.get("message", {}).get("role") if isinstance(record.get("message"), dict) else record.get("role")
    if role not in (None, "assistant"):
        return None

    msg = record.get("message")
    if isinstance(msg, dict):
        content = msg.get("content")
    else:
        content = record.get("content")

    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        joined = "\n".join(p for p in parts if p).strip()
        return joined or None
    if isinstance(record.get("text"), str):
        return record["text"].strip() or None
    return None


def from_jsonl(path: str | Path, *, source: str = "", trace_id: str = "") -> RawTrace:
    """Ingest a .jsonl transcript into a single RawTrace of assistant steps.

    Format-tolerant: it keeps whatever assistant text it can extract, in order,
    and ignores the rest. Segmenting a long session into per-problem episodes is a
    judgement call left to the judge (which can mark rumination within a run); this
    just gets the ordered text in.
    """
    p = Path(path)
    steps: list[TraceStep] = []
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            text = _extract_text(record)
            if text:
                steps.append(TraceStep(text=text, index=len(steps)))
    return RawTrace(steps=steps, source=source or str(p), trace_id=trace_id or p.stem)


def save_traces(traces: Iterable[Any], path: str | Path) -> None:
    """Write RawTraces or ScoredTraces to a JSON file (list of dicts)."""
    payload = [t.to_dict() for t in traces]
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_scored_traces(path: str | Path) -> list[ScoredTrace]:
    """Read a JSON file of ScoredTraces back."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [ScoredTrace.from_dict(d) for d in data]


def load_raw_traces(path: str | Path) -> list[RawTrace]:
    """Read a JSON file of RawTraces back."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RawTrace.from_dict(d) for d in data]
