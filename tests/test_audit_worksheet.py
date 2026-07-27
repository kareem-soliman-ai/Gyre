"""Blinded expert-audit worksheet and its absorber.

The escape bound is only worth anything if the expert judged the auto-approved
steps WITHOUT seeing what the panel decided. So the worksheet must leak nothing:
no labels, no probabilities, no provenance, no ordering that groups approved
items together. These tests pin that, and pin the absorber that turns ticked
boxes back into an escape bound and an expert-anchored qualification set.
"""

import pytest

from gyre.audit_worksheet import (
    AuditItem,
    absorb_worksheet,
    render_worksheet,
    sample_audit_items,
)


def _labelled_records():
    steps = []
    for i in range(40):
        steps.append({
            "index": i,
            "text": f"step {i} did a thing\n[obs] result {i}",
            "is_ruminating": i % 4 == 0,
            "provenance": "auto" if i % 5 else "human_needed",
            "p_rum": 0.9 if i % 4 == 0 else 0.1,
            "width": 0.05,
        })
    return [{"trace_id": "t1", "source": "s", "steps": steps}]


# --- sampling --------------------------------------------------------------------


def test_sample_takes_auto_approved_and_all_disputed():
    items = sample_audit_items(_labelled_records(), n_auto=10, seed=1)
    kinds = [i.kind for i in items]
    assert kinds.count("audit") == 10
    assert kinds.count("anchor") == sum(
        1 for s in _labelled_records()[0]["steps"] if s["provenance"] == "human_needed"
    )


def test_sample_is_deterministic_for_a_seed():
    a = sample_audit_items(_labelled_records(), n_auto=8, seed=7)
    b = sample_audit_items(_labelled_records(), n_auto=8, seed=7)
    assert [i.item_id for i in a] == [i.item_id for i in b]


def test_sample_refuses_to_oversample():
    with pytest.raises(ValueError):
        sample_audit_items(_labelled_records(), n_auto=10_000, seed=1)


def test_items_are_shuffled_so_kind_is_not_guessable_from_position():
    items = sample_audit_items(_labelled_records(), n_auto=15, seed=3)
    kinds = [i.kind for i in items]
    # both kinds must appear in the first and second half
    half = len(kinds) // 2
    assert set(kinds[:half]) == set(kinds[half:]) == {"audit", "anchor"}


# --- blinding --------------------------------------------------------------------


def test_rendered_worksheet_leaks_no_panel_verdict():
    items = sample_audit_items(_labelled_records(), n_auto=10, seed=1)
    text = render_worksheet(items)
    for forbidden in ("is_ruminating", "p_rum", "provenance", "auto", "anchor",
                      "human_needed", "panel said", "0.9"):
        assert forbidden not in text, f"worksheet leaks {forbidden!r}"


def test_rendered_worksheet_has_one_tickbox_per_item_and_context():
    items = sample_audit_items(_labelled_records(), n_auto=5, seed=1)
    text = render_worksheet(items)
    assert text.count("[ ] ruminating") == len(items)
    assert text.count("[ ] productive") == len(items)
    for i in items:
        assert i.item_id in text


# --- absorbing -------------------------------------------------------------------


def test_absorb_reads_ticks_and_matches_them_back_to_hidden_labels():
    items = sample_audit_items(_labelled_records(), n_auto=10, seed=1)
    marked = render_worksheet(items).replace("[ ] ruminating", "[x] ruminating")
    result = absorb_worksheet(marked, items)
    assert result.n_marked == len(items)
    assert all(v is True for v in result.expert_labels.values())


def test_absorb_ignores_unmarked_items_rather_than_guessing():
    items = sample_audit_items(_labelled_records(), n_auto=6, seed=1)
    text = render_worksheet(items)  # nothing ticked
    result = absorb_worksheet(text, items)
    assert result.n_marked == 0
    assert result.expert_labels == {}


def test_absorb_rejects_an_item_ticked_both_ways():
    items = sample_audit_items(_labelled_records(), n_auto=3, seed=1)
    text = render_worksheet(items).replace("[ ] ruminating", "[x] ruminating").replace(
        "[ ] productive", "[x] productive"
    )
    result = absorb_worksheet(text, items)
    assert result.conflicts
    assert result.n_marked == 0


def test_escape_bound_counts_only_audit_items_where_expert_disagrees():
    items = sample_audit_items(_labelled_records(), n_auto=12, seed=1)
    # expert agrees with every hidden panel label
    text = render_worksheet(items)
    for i in items:
        tick = "[x] ruminating" if i.hidden_label else "[x] productive"
        text = text.replace(
            f"{i.item_id}\n[ ] ruminating", f"{i.item_id}\n[ ] ruminating"
        )
    marks = {i.item_id: bool(i.hidden_label) for i in items}
    result = absorb_worksheet(text, items, marks=marks)
    assert result.escapes == 0
    assert result.audited == sum(1 for i in items if i.kind == "audit")
    assert result.bound.claimable


def test_key_round_trips_through_json():
    from gyre.audit_worksheet import items_from_json, items_to_json

    items = sample_audit_items(_labelled_records(), n_auto=6, seed=2)
    back = items_from_json(items_to_json(items))
    assert [i.item_id for i in back] == [i.item_id for i in items]
    assert [i.hidden_label for i in back] == [i.hidden_label for i in items]
    assert [i.kind for i in back] == [i.kind for i in items]
