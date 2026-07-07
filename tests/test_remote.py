"""Proof that measurements can live off-machine without the loop knowing.

This is the test that answers "can we keep the proprietary scoring out of the
repo and serve it over the wire?" A ``FakeScoringServer`` stands in for a hosted
GCP endpoint: it holds the (would-be proprietary) scoring logic, keys state by
session, and speaks the same JSON contract the real HTTP transport uses. The
client (``RemoteMeasurementProvider``) carries none of that logic.

The key assertion is ``test_remote_provider_drives_loop_like_a_local_one``: the
same RuminationMonitor catches the same hidden rumination whether the sensor is
local or remote. No network, no cloud spend, no scoring logic in the client.
"""

import json

from gyre import ExitReason, Meaning, Measurement, RuminationMonitor
from gyre.bench import LabelledTrace, compare_providers
from gyre.providers import DiffNoveltyProvider, RemoteMeasurementProvider


class _Obs:
    """Observation carrying a surface artifact and a hidden concept id."""

    def __init__(self, artifact: str, concept: int) -> None:
        self.artifact = artifact
        self.concept = concept


class FakeScoringServer:
    """Stands in for a hosted scoring service holding proprietary logic.

    It runs a toy semantic rumination detector server-side, keeps per-session
    state (as a real stateful sensor would), and returns Measurements as JSON.
    Crucially, none of this lives in the client. The client just posts
    observations and gets readings back.
    """

    def __init__(self) -> None:
        self._state: dict[str, int] = {}
        self.calls = 0

    def handle(self, payload: dict) -> dict:
        # Exercise real serialisation so the test proves the wire format, not just
        # object passing: round-trip the payload through JSON.
        payload = json.loads(json.dumps(payload))
        self.calls += 1
        op = payload["op"]
        session = payload.get("session", "default")
        if op == "reset":
            self._state.pop(session, None)
            return {}
        obs = payload["observation"]
        concept = obs["concept"]
        prev = self._state.get(session)
        ruminating = prev is not None and concept == prev
        self._state[session] = concept
        return Measurement(
            value=0.0 if ruminating else 1.0,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            decision=ruminating,
            probability=1.0 if ruminating else 0.0,
            provider="remote:fake-semantic",
        ).to_dict()


def _stream():
    surfaces = [
        "alpha bravo charlie",
        "xray yankee zulu",
        "one two three four",
        "crimson viridian cerulean",
        "north south east west",
    ]
    concepts = [0, 1, 1, 1, 1]
    return [_Obs(s, c) for s, c in zip(surfaces, concepts)]


def test_measurement_survives_a_json_round_trip():
    m = Measurement(
        value=0.4,
        meaning=Meaning.LOWER_IS_HEALTHIER,
        standardized=1.2,
        probability=0.7,
        decision=True,
        measurement_error=0.05,
        confounds=("a", "b"),
        provider="x",
        detail={"n": 3},
    )
    back = Measurement.from_dict(json.loads(json.dumps(m.to_dict())))
    assert back == m


def test_remote_provider_drives_loop_like_a_local_one():
    server = FakeScoringServer()
    remote = RemoteMeasurementProvider("L1", "remote:fake-semantic", server.handle)
    monitor = RuminationMonitor(remote, patience=3)  # no threshold: server is calibrated

    for obs in _stream():
        monitor.observe(obs)

    assert monitor.verdict().exit_reason is ExitReason.REFRAME  # caught it, over the wire
    assert server.calls >= 5  # the scoring genuinely happened server-side


def test_remote_reset_propagates_to_the_server():
    server = FakeScoringServer()
    remote = RemoteMeasurementProvider("L1", "remote:fake-semantic", server.handle)
    monitor = RuminationMonitor(remote, patience=3)
    for obs in _stream():
        monitor.observe(obs)
    monitor.reset()
    assert server._state == {}  # server dropped the session on reset


def test_remote_provider_works_in_the_benchmark():
    server = FakeScoringServer()
    remote = RemoteMeasurementProvider("L1", "remote:fake-semantic", server.handle)
    trace = LabelledTrace(
        observations=_stream(),
        labels=[False, False, True, True, True],
        loop_id="L1",
    )
    ranked = compare_providers([DiffNoveltyProvider(), remote], [trace])
    # The remote (proprietary-style) sensor wins the head-to-head, same as a local one.
    assert ranked[0].provider == "remote:fake-semantic"
    assert ranked[0].calibrated is True
