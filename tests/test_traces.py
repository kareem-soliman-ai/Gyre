"""Trace format and ingestion tests."""

import json

from gyre.traces import (
    RawTrace,
    ScoredStep,
    ScoredTrace,
    TraceStep,
    from_jsonl,
    load_scored_traces,
    save_traces,
)


def test_raw_trace_round_trips():
    tr = RawTrace(steps=[TraceStep("a", index=0), TraceStep("b", index=1)], trace_id="t1")
    assert RawTrace.from_dict(tr.to_dict()) == tr


def test_scored_trace_to_bench_maps_steps_and_labels():
    st = ScoredTrace(
        steps=[
            ScoredStep("first attempt", is_ruminating=False, index=0),
            ScoredStep("same thing again", is_ruminating=True, index=1),
        ],
        trace_id="t2",
    )
    bench = st.to_bench("L1")
    assert bench.loop_id == "L1"
    assert bench.labels == [False, True]
    assert bench.observations[1].artifact == "same thing again"


def test_from_jsonl_is_format_tolerant(tmp_path):
    # Mix of shapes: Claude-Code-style content blocks, a plain role/content, and a
    # non-assistant line that should be skipped.
    lines = [
        {"type": "assistant", "message": {"role": "assistant",
         "content": [{"type": "text", "text": "step one"}]}},
        {"role": "assistant", "content": "step two"},
        {"role": "user", "content": "not an agent step"},
        {"type": "assistant", "message": {"role": "assistant",
         "content": [{"type": "text", "text": "step three"}]}},
    ]
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")

    tr = from_jsonl(p)
    texts = [s.text for s in tr.steps]
    assert texts == ["step one", "step two", "step three"]  # user line skipped


def test_save_and_load_scored_traces(tmp_path):
    st = ScoredTrace(steps=[ScoredStep("x", is_ruminating=True, index=0)], trace_id="t3")
    path = tmp_path / "corpus.json"
    save_traces([st], path)
    back = load_scored_traces(path)
    assert back[0].steps[0].is_ruminating is True
    assert back[0].trace_id == "t3"
