"""Trace format and ingestion tests."""

import json

from gyre.traces import (
    RawTrace,
    ScoredStep,
    ScoredTrace,
    TraceStep,
    from_agentic_run,
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


def _agentic_run():
    return {
        "model": "test/model",
        "repeat": 1,
        "passed": False,
        "tokens_in": 10,
        "tokens_out": 20,
        "cost_usd": 0.01,
        "verifier_errors": ["output file missing"],
        "trace": [
            {
                "step": 0,
                "action": {"action": "list_dir", "path": "."},
                "raw": '{"action": "list_dir", "path": "."}',
                "observation": "a.txt\nb.txt",
            },
            {
                "step": 1,
                "action": {"action": "read_file", "path": "a.txt"},
                "raw": '{"action": "read_file", "path": "a.txt"}',
                "observation": "hello world",
            },
        ],
    }


def test_from_agentic_run_maps_act_observe_steps_to_legible_text():
    tr = from_agentic_run(_agentic_run(), trace_id="r1")
    assert tr.trace_id == "r1"
    assert len(tr.steps) == 2
    # the action name and its target must be in the step text (rumination =
    # repeated action on the same target, so the target is load-bearing)
    assert "list_dir" in tr.steps[0].text
    assert "read_file" in tr.steps[1].text and "a.txt" in tr.steps[1].text
    # the observation rides along so evidence-arrival sensors can see it
    assert "hello world" in tr.steps[1].text
    assert tr.steps[1].index == 1


def test_from_agentic_run_keeps_outcome_labels_in_meta():
    tr = from_agentic_run(_agentic_run(), trace_id="r1")
    assert tr.meta["passed"] is False
    assert tr.meta["cost_usd"] == 0.01
    assert tr.meta["tokens_out"] == 20
    assert tr.meta["verifier_errors"] == ["output file missing"]


def test_from_agentic_run_loads_from_a_json_file(tmp_path):
    p = tmp_path / "run.json"
    p.write_text(json.dumps(_agentic_run()), encoding="utf-8")
    tr = from_agentic_run(p)
    assert tr.trace_id == "run"
    assert len(tr.steps) == 2
    assert tr.meta["model"] == "test/model"
