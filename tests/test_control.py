"""Tests for the public control seam and reference controllers."""

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


def _verdict(reason, loop_id="L1", measurements=()):
    return LoopVerdict(exit_reason=reason, loop_id=loop_id, measurements=measurements)


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
