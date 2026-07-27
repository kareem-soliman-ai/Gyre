"""Exact-counterfactual replay on outcome-labelled traces.

The asymmetry this rests on: on a run that FAILED, stopping early costs you
nothing, because the run failed anyway. That makes the saving exact rather than
simulated. On a run that PASSED, stopping early loses the success, and we
charge the full value of it. No other counterfactual assumption is made.
"""

import pytest

from gyre.replay import ReplayRun, net_value_curve, replay_policy


def _runs():
    return [
        # 10 steps each; failures are where saving is possible
        ReplayRun(steps=[f"fail-{i} same same same" for i in range(10)],
                  succeeded=False, cost=1.0, run_id="f1"),
        ReplayRun(steps=[f"work-{i} genuinely new content {i}" for i in range(10)],
                  succeeded=True, cost=1.0, run_id="p1"),
    ]


class _FireAt:
    """A stand-in sensor that fires at a fixed step index."""

    loop_id = "L1"

    def __init__(self, at: int | None):
        self.name = f"fire@{at}"
        self._at = at
        self._i = -1

    def measure(self, observation):
        from gyre.measurement import Meaning, Measurement

        self._i += 1
        fire = self._at is not None and self._i >= self._at
        return Measurement(
            value=0.0 if fire else 1.0,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            decision=fire,
            provider=self.name,
        )

    def reset(self):
        self._i = -1


# --- the exact counterfactual ----------------------------------------------------


def test_a_sensor_that_never_fires_changes_nothing():
    out = replay_policy(_runs(), lambda: _FireAt(None), value_of_success=1.0)
    assert out.cost_saved == 0.0
    assert out.successes_lost == 0
    assert out.net_value == 0.0


def test_stopping_a_failed_run_early_saves_its_tail_and_loses_nothing():
    # fires at step 4 of 10 -> 5 remaining steps saved on the failed run
    out = replay_policy(_runs(), lambda: _FireAt(4), value_of_success=1.0)
    assert out.cost_saved == pytest.approx(0.5, abs=0.11)
    assert out.successes_lost == 1  # the passing run was also truncated


def test_truncating_a_successful_run_is_charged_at_the_value_of_success():
    cheap = replay_policy(_runs(), lambda: _FireAt(4), value_of_success=0.1)
    dear = replay_policy(_runs(), lambda: _FireAt(4), value_of_success=10.0)
    assert cheap.net_value > dear.net_value
    assert dear.net_value < 0  # when success is precious, early stopping is a loss


def test_saving_is_proportional_to_how_early_the_stop_happens():
    early = replay_policy(_runs(), lambda: _FireAt(1), value_of_success=0.0)
    late = replay_policy(_runs(), lambda: _FireAt(8), value_of_success=0.0)
    assert early.cost_saved > late.cost_saved


def test_replay_reports_per_run_detail():
    out = replay_policy(_runs(), lambda: _FireAt(4), value_of_success=1.0)
    assert len(out.per_run) == 2
    assert {r["run_id"] for r in out.per_run} == {"f1", "p1"}
    assert all("onset" in r for r in out.per_run)


def test_empty_corpus_is_rejected_rather_than_scored_as_zero():
    with pytest.raises(ValueError):
        replay_policy([], lambda: _FireAt(1), value_of_success=1.0)


# --- the regime sweep ------------------------------------------------------------


def test_curve_covers_every_requested_regime():
    curve = net_value_curve(_runs(), lambda: _FireAt(4), values=[0.0, 1.0, 5.0])
    assert [p.value_of_success for p in curve] == [0.0, 1.0, 5.0]


def test_net_value_falls_monotonically_as_success_gets_more_valuable():
    curve = net_value_curve(_runs(), lambda: _FireAt(4), values=[0.0, 1.0, 5.0, 20.0])
    nets = [p.net_value for p in curve]
    assert nets == sorted(nets, reverse=True)


def test_a_policy_that_never_fires_is_flat_across_regimes():
    curve = net_value_curve(_runs(), lambda: _FireAt(None), values=[0.0, 5.0, 50.0])
    assert len({round(p.net_value, 9) for p in curve}) == 1
