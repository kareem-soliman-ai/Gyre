"""Runnable, offline demonstration of the whole strategy in one file.

Spins up an in-process stand-in for a hosted scoring service, then scores a naive
local sensor and a remote (proprietary-style) sensor head to head on the same
labelled trace. Shows two things at once:

1. The loop is identical for both; only the sensor is swapped.
2. The remote sensor, whose scoring lives server-side and never touches this
   file's logic, wins.

Run it:  python scripts/demo_remote_vs_naive.py

No network, no cloud spend. The "server" is a local object. Swap its handler for
``gyre.providers.http_transport("https://your-endpoint")`` and the exact same
client code talks to a real hosted scorer.
"""

from __future__ import annotations

from gyre import Meaning, Measurement
from gyre.bench import LabelledTrace, compare_providers
from gyre.providers import DiffNoveltyProvider, RemoteMeasurementProvider


class Obs:
    def __init__(self, artifact: str, concept: int) -> None:
        self.artifact = artifact
        self.concept = concept


class LocalStandInServer:
    """Pretends to be a hosted scorer. Holds the (would-be proprietary) logic;
    the client below never sees it."""

    def __init__(self) -> None:
        self._state: dict[str, int] = {}

    def handle(self, payload: dict) -> dict:
        if payload["op"] == "reset":
            self._state.pop(payload.get("session", "default"), None)
            return {}
        session = payload.get("session", "default")
        concept = payload["observation"]["concept"]
        ruminating = self._state.get(session) == concept
        self._state[session] = concept
        return Measurement(
            value=0.0 if ruminating else 1.0,
            meaning=Meaning.HIGHER_IS_HEALTHIER,
            decision=ruminating,
            provider="remote:proprietary-ish",
        ).to_dict()


def main() -> None:
    # An agent that keeps landing on the same fix (concept 1 from step 1) while
    # rewording it completely each time. Rumination hidden under lexical novelty.
    surfaces = [
        "alpha bravo charlie",
        "xray yankee zulu",
        "one two three four",
        "crimson viridian cerulean",
        "north south east west",
    ]
    concepts = [0, 1, 1, 1, 1]
    labels = [False, False, True, True, True]  # ground truth: stuck from step 2
    trace = LabelledTrace(
        observations=[Obs(s, c) for s, c in zip(surfaces, concepts)],
        labels=labels,
        loop_id="L1",
    )

    server = LocalStandInServer()
    providers = [
        DiffNoveltyProvider(),  # naive, local, lexical
        RemoteMeasurementProvider("L1", "remote:proprietary-ish", server.handle),
    ]

    print("Scoring two sensors on the same hidden-rumination trace:\n")
    print(f"  {'sensor':28}  {'F1':>5}  {'recall':>6}  where scoring runs / threshold")
    print("  " + "-" * 74)
    for s in compare_providers(providers, [trace]):
        where = "server-side, no threshold" if s.calibrated else f"local, swept theta={s.best_threshold}"
        print(f"  {s.provider:28}  {s.f1:5.2f}  {s.recall:6.2f}  {where}")

    print(
        "\nThe naive lexical sensor sees five very different strings and thinks the\n"
        "agent is exploring. The remote sensor, whose logic never entered this file,\n"
        "catches the repeated concept. Same loop. Different sensor. Different result."
    )


if __name__ == "__main__":
    main()
