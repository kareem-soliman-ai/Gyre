"""Tests for the meta-bandit L7 controller (machinery F1 from the taxonomy).

The meta-bandit:
- Selects among multiple controllers (arms) to maximize reward
- Uses UCB1 to balance exploration and exploitation
- Does not make any world-model assumptions

The falsifier from the mapping:
- If a single fixed controller dominates across all cells, the meta-layer
  is dead weight and should be dropped.
- This test verifies the bandit's selection and reward mechanics.
"""

import pytest

from gyre.control import ControlContext, FixedRouteController
from gyre.control.meta_bandit import MetaBanditController
from gyre.interfaces import ExitReason, LoopVerdict
from gyre.measurement import Meaning, Measurement


def _verdict(reason, loop_id="L1", measurements=()):
    return LoopVerdict(exit_reason=reason, loop_id=loop_id, measurements=measurements)


def _l1_measurement(prob=0.95):
    return Measurement(
        value=1 - prob,
        meaning=Meaning.HIGHER_IS_HEALTHIER,
        probability=prob,
        decision=prob >= 0.5,
        provider="test:l1",
    )


CTX = ControlContext(divergent=True, steps_remaining=10)


# ---------------------------------------------------------------------------
# Basic functionality
# ---------------------------------------------------------------------------

def test_meta_bandit_has_at_least_one_arm():
    """MetaBanditController must have at least one controller."""
    with pytest.raises(ValueError):
        MetaBanditController()


def test_meta_bandit_routes_yes_something():
    """The bandit should return a valid ExitReason."""
    from gyre.control import FixedRouteController
    bandit = MetaBanditController(controllers=[
        FixedRouteController(ExitReason.REFRAME),
        FixedRouteController(ExitReason.ESCALATE),
    ])
    result = bandit.route([_verdict(ExitReason.PLATEAU)], CTX)
    assert result in (ExitReason.REFRAME, ExitReason.ESCALATE)


def test_meta_bandit_rupture_preempts():
    """RUPTURE should always be passed through, regardless of the bandit."""
    from gyre.control import FixedRouteController
    bandit = MetaBanditController(controllers=[
        FixedRouteController(ExitReason.REFRAME),
        FixedRouteController(ExitReason.ESCALATE),
    ])
    verdicts = [_verdict(ExitReason.RUPTURE, "L3")]
    result = bandit.route(verdicts, CTX)
    assert result is ExitReason.RUPTURE


def test_meta_bandit_resets_correctly():
    from gyre.control import FixedRouteController
    bandit = MetaBanditController(controllers=[
        FixedRouteController(ExitReason.REFRAME),
        FixedRouteController(ExitReason.ESCALATE),
    ])
    # Play a few rounds
    for _ in range(5):
        bandit.route([_verdict(ExitReason.PLATEAU)], CTX)
    # Reset
    bandit.reset()
    report = bandit.arm_report()
    for arm in report:
        assert arm["visits"] == 0
        assert arm["avg_reward"] == 0.0


# ---------------------------------------------------------------------------
# UCB1 dynamics
# ---------------------------------------------------------------------------

def test_ucb1_exploration():
    """After enough play, all arms should be explored."""
    from gyre.control import FixedRouteController
    bandit = MetaBanditController(controllers=[
        FixedRouteController(ExitReason.REFRAME),
        FixedRouteController(ExitReason.ESCALATE),
        FixedRouteController(ExitReason.ABANDON),
    ])
    for _ in range(20):
        bandit.route([_verdict(ExitReason.PLATEAU)], CTX)
    report = bandit.arm_report()
    # All arms should have been visited at least once
    for arm in report:
        assert arm["visits"] > 0, f"Arm {arm['name']} was never visited"


def test_ucb1_rewards_accumulate():
    """The arm reward system should accumulate correctly."""
    from gyre.control import FixedRouteController
    bandit = MetaBanditController(controllers=[
        FixedRouteController(ExitReason.REFRAME),
        FixedRouteController(ExitReason.ESCALATE),
    ])
    # Play some rounds with a known context
    for _ in range(10):
        bandit.route([_verdict(ExitReason.PLATEAU)], CTX)
    report = bandit.arm_report()
    total_visits = sum(a["visits"] for a in report)
    assert total_visits == 10


def test_arm_report_returns_correct_shape():
    """arm_report should return a list of dicts with the right keys."""
    from gyre.control import FixedRouteController
    bandit = MetaBanditController(controllers=[
        FixedRouteController(ExitReason.REFRAME),
        FixedRouteController(ExitReason.ESCALATE),
    ])
    report = bandit.arm_report()
    assert isinstance(report, list)
    assert len(report) == 2
    for arm in report:
        assert "name" in arm
        assert "visits" in arm
        assert "avg_reward" in arm
        assert "total_reward" in arm


def test_reward_computation():
    """Rewards should be stakes minus the cost of the chosen route."""
    from gyre.control.meta_bandit import MetaBanditController
    from gyre.control import FixedRouteController
    bandit = MetaBanditController(controllers=[
        FixedRouteController(ExitReason.CONTINUE),
        FixedRouteController(ExitReason.REFRAME),
        FixedRouteController(ExitReason.ESCALATE),
        FixedRouteController(ExitReason.ABANDON),
    ])
    # Test the reward function
    ctx = ControlContext(stakes=1.0, step_cost=0.05, reframe_cost=0.1, escalation_cost=0.6)
    assert bandit._compute_reward(ExitReason.CONTINUE, ctx) == 0.95
    assert bandit._compute_reward(ExitReason.REFRAME, ctx) == 0.9
    assert bandit._compute_reward(ExitReason.ESCALATE, ctx) == 0.4
    assert bandit._compute_reward(ExitReason.ABANDON, ctx) == 1.0