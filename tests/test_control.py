"""Tests for the control seam: the public interface and reference controllers
always run; the proprietary adaptive controller tests SKIP on a clean public
checkout, following the pattern in test_proprietary_mvt.py."""

import pytest

from gyre.control import (
    ControlContext,
    FixedRouteController,
    L5RouteController,
    MetaController,
    available,
    dominant_verdict,
    get_controller,
)
from gyre.interfaces import ExitReason, LoopVerdict
from gyre.measurement import Meaning, Measurement


def _verdict(reason, loop_id="L1", measurements=()):
    return LoopVerdict(exit_reason=reason, loop_id=loop_id, measurements=measurements)


def _l1_measurement(prob):
    return Measurement(
        value=1 - prob, meaning=Meaning.HIGHER_IS_HEALTHIER,
        probability=prob, decision=prob >= 0.5, provider="test:l1",
    )


CTX = ControlContext()


def test_seek_info_is_a_route():
    assert ExitReason.SEEK_INFO.value == "seek_info"


def test_rupture_preempts_everything():
    verdicts = [_verdict(ExitReason.PLATEAU), _verdict(ExitReason.RUPTURE, "L3")]
    assert dominant_verdict(verdicts).exit_reason is ExitReason.RUPTURE
    for controller in (FixedRouteController(ExitReason.ESCALATE), L5RouteController()):
        assert controller.route(verdicts, CTX) is ExitReason.RUPTURE


def test_quiet_verdicts_mean_continue():
    verdicts = [_verdict(ExitReason.CONTINUE), _verdict(ExitReason.CONTINUE, "L2")]
    assert dominant_verdict(verdicts) is None
    assert FixedRouteController().route(verdicts, CTX) is ExitReason.CONTINUE


def test_fixed_controller_takes_its_configured_route():
    verdicts = [_verdict(ExitReason.PLATEAU)]
    assert FixedRouteController(ExitReason.ABANDON).route(verdicts, CTX) is ExitReason.ABANDON


def test_l5_controller_conditions_on_problem_type():
    verdicts = [_verdict(ExitReason.PLATEAU)]
    c = L5RouteController()
    assert c.route(verdicts, ControlContext(divergent=True)) is ExitReason.REFRAME
    assert c.route(verdicts, ControlContext(divergent=False)) is ExitReason.ESCALATE
    # unknown problem type is treated as convergent: escalate, conservatively
    assert c.route(verdicts, ControlContext(divergent=None)) is ExitReason.ESCALATE


def test_registry_serves_reference_controllers():
    assert {"fixed:reframe", "fixed:escalate", "fixed:abandon", "l5-informed"} <= set(available())
    c = get_controller("l5-informed")
    assert isinstance(c, MetaController)


# --- proprietary tier ---------------------------------------------------------

adaptive = pytest.importorskip("gyre.control.proprietary.adaptive_ev")


def _controller(**kw):
    kw.setdefault("sensor_tpr", 0.96)
    kw.setdefault("sensor_fpr", 0.11)
    return adaptive.AdaptiveEVController(**kw)


def test_adaptive_registered():
    assert "psy:adaptive-ev" in available()


def test_adaptive_belief_rises_on_low_gain_flags_and_routes_out():
    """Feed a stream of confident 'ruminating' readings: belief in stuck climbs
    until the controller routes off CONTINUE (REFRAME, given a divergent
    problem and budget), and each reframe deflates the belief — the reset
    probably unstuck the loop, and the controller's model says so."""
    c = _controller()
    ctx = ControlContext(divergent=True, steps_remaining=10)
    beliefs, routes = [], []
    for _ in range(6):
        r = c.route([_verdict(ExitReason.CONTINUE, measurements=(_l1_measurement(0.95),))], ctx)
        beliefs.append(c.belief_stuck)
        routes.append(r)
    assert routes[0] is ExitReason.CONTINUE          # one flag is not evidence enough
    assert beliefs[1] > beliefs[0]                   # sustained flags accumulate
    assert ExitReason.REFRAME in routes              # ...and route out
    first_reframe = routes.index(ExitReason.REFRAME)
    assert beliefs[first_reframe + 1] < beliefs[first_reframe]  # reframe deflates belief


def test_adaptive_holds_on_healthy_readings():
    c = _controller()
    ctx = ControlContext(divergent=True, steps_remaining=10)
    for _ in range(8):
        r = c.route([_verdict(ExitReason.CONTINUE, measurements=(_l1_measurement(0.02),))], ctx)
        assert r is ExitReason.CONTINUE
    assert c.belief_stuck < 0.5


def test_adaptive_escalates_convergent_problems_when_stuck():
    c = _controller()
    ctx = ControlContext(divergent=False, steps_remaining=10)
    routes = [
        c.route([_verdict(ExitReason.CONTINUE, measurements=(_l1_measurement(0.95),))], ctx)
        for _ in range(6)
    ]
    assert ExitReason.ESCALATE in routes
    assert ExitReason.REFRAME not in routes          # reframe rarely pays on convergent


def test_adaptive_respects_escalation_cost():
    """The E2 brittleness result at the unit level: same signals, different cost
    regime, different route. When human attention is expensive relative to the
    stakes, the controller must stop choosing ESCALATE."""
    cheap = ControlContext(divergent=False, steps_remaining=10, escalation_cost=0.6)
    dear = ControlContext(divergent=False, steps_remaining=10, escalation_cost=2.5)
    routes_cheap, routes_dear = [], []
    c1, c2 = _controller(), _controller()
    for _ in range(6):
        v = [_verdict(ExitReason.CONTINUE, measurements=(_l1_measurement(0.95),))]
        routes_cheap.append(c1.route(v, cheap))
        routes_dear.append(c2.route(v, dear))
    assert ExitReason.ESCALATE in routes_cheap
    assert ExitReason.ESCALATE not in routes_dear


def test_adaptive_rupture_preempts():
    c = _controller()
    verdicts = [_verdict(ExitReason.RUPTURE, "L3")]
    assert c.route(verdicts, CTX) is ExitReason.RUPTURE


def test_adaptive_requires_threshold_for_uncalibrated_sensor():
    from gyre.loops._policy import ThresholdRequired

    raw = Measurement(value=0.01, meaning=Meaning.HIGHER_IS_HEALTHIER, provider="raw")
    c = _controller()
    with pytest.raises(ThresholdRequired):
        c.route([_verdict(ExitReason.CONTINUE, measurements=(raw,))], CTX)
    c2 = _controller(flag_threshold=0.2)
    assert c2.route(
        [_verdict(ExitReason.CONTINUE, measurements=(raw,))],
        ControlContext(divergent=True, steps_remaining=10),
    ) in (ExitReason.CONTINUE, ExitReason.REFRAME)
