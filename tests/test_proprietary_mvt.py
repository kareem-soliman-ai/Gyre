"""Tests for the gitignored proprietary L1 providers.

These SKIP in a clean public checkout (the module is gitignored and absent) and
run in a checkout that has the private layer. That is deliberate: the public CI
proves the architecture, and Kareem's checkout proves the sensor.
"""

import pytest

# Skip the whole module if the proprietary layer (or numpy) is not present.
mvt = pytest.importorskip("gyre.providers.proprietary.mvt_rumination")

from gyre.bench import LabelledTrace, compare_providers  # noqa: E402
from gyre.loops.rumination import IterationObservation, RuminationMonitor  # noqa: E402
from gyre.providers import DiffNoveltyProvider, available  # noqa: E402


def _hidden_rumination_trace():
    # Semantically repeated fix (the agent circles the same patch) with light
    # surface variation. Labels: stuck from step 2 on.
    surfaces = [
        "def fix(): return compute_alpha(x) + 1",
        "refactor the parser to handle the tokenize edge case",
        "def fix(): return compute_alpha(x) + 1  # retry",
        "def fix(): return compute_alpha(x) + 1  # try again",
        "def fix(): return compute_alpha(x) + 1  # once more",
    ]
    labels = [False, False, True, True, True]
    obs = [IterationObservation(artifact=s, index=i) for i, s in enumerate(surfaces)]
    return LabelledTrace(observations=obs, labels=labels, loop_id="L1")


def test_proprietary_providers_are_discovered():
    assert "psy:mvt-rumination" in available("L1")


def test_mvt_beats_naive_on_hidden_rumination():
    trace = _hidden_rumination_trace()
    ranked = compare_providers(
        [DiffNoveltyProvider(), mvt.MvtRuminationProvider()], [trace]
    )
    assert ranked[0].provider == "psy:mvt-rumination"
    assert ranked[0].calibrated is True  # no threshold needed
    assert ranked[0].f1 >= ranked[1].f1


def test_mvt_provider_drives_the_loop_and_needs_no_threshold():
    monitor = RuminationMonitor(mvt.MvtRuminationProvider(), patience=2)
    for obs in _hidden_rumination_trace().observations:
        monitor.observe(obs)
    # It should have routed off CONTINUE by the end of a rumination run.
    assert monitor.verdict().exit_reason.value != "continue"
