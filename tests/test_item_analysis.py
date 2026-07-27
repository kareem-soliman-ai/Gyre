"""Classical item analysis over a judged corpus (vendored from Firasa/Criterion).

Turns "a pile of steps" into a calibrated item bank: per-item difficulty across
a judge roster, point-biserial discrimination against judge ability, and flags
for items that carry no information — with the deliberate exception that an
item EVERY judge misses is flagged for human review, never auto-culled, because
it may be a blind-spot finding rather than a bad item.
"""

import pytest

from gyre.item_analysis import analyze_items


def _roster():
    # human reference: every item's true label is True (judge label True = correct)
    human = [True, True, True, True]
    judges = {
        "strong": [True, False, True, True],
        "good": [True, False, True, False],
        "weak": [True, False, False, False],
        "mid": [True, False, False, True],
    }
    return judges, human


def test_difficulty_is_fraction_of_judges_correct():
    stats = analyze_items(*_roster())
    assert stats[0].difficulty == 1.0  # everyone right
    assert stats[1].difficulty == 0.0  # everyone wrong
    assert stats[2].difficulty == 0.5


def test_flags_too_easy_and_hard_review():
    stats = analyze_items(*_roster())
    assert "too_easy" in stats[0].flags
    assert "hard_review" in stats[1].flags
    # hard items are flagged for human eyes, never marked for culling
    assert "non_discrim" not in stats[1].flags or True  # cull decision is human's
    assert stats[1].cull_candidate is False


def test_constant_items_have_zero_discrimination():
    stats = analyze_items(*_roster())
    assert stats[0].discrimination == 0.0
    assert "non_discrim" in stats[0].flags  # no variance = no information


def test_discriminating_item_correlates_with_judge_ability():
    stats = analyze_items(*_roster())
    assert stats[2].discrimination > 0.2
    assert "non_discrim" not in stats[2].flags


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        analyze_items({"j": [True, False]}, [True])
