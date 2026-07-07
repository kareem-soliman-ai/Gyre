"""Interfaces smoke tests.

These do not test a detector, because v0.1 ships no detectors. They check that
the vocabulary layer imports, that the types compose, and that a hand-written
monitor satisfies the LoopMonitor protocol. That is the whole contract at this
stage: the shape is real and usable, even though nothing scores anything yet.
"""

from gyre import (
    ExitReason,
    LoopMonitor,
    LoopSignal,
    LoopVerdict,
    Maturity,
    __version__,
)


def test_version_is_present():
    assert __version__ == "0.1.0"


def test_signal_carries_its_confounds():
    sig = LoopSignal(
        loop_id="L1",
        name="diff_novelty_ratio",
        value=0.03,
        confounds=("rewards thrashing", "lexical not semantic"),
    )
    assert sig.loop_id == "L1"
    assert "rewards thrashing" in sig.confounds


def test_verdict_defaults_are_honest():
    # An unvalidated monitor should not fake a confidence number.
    verdict = LoopVerdict(exit_reason=ExitReason.PLATEAU)
    assert verdict.confidence is None
    assert verdict.maturity is Maturity.BUILDABLE


def test_hand_written_monitor_satisfies_protocol():
    class TrivialMonitor:
        loop_id = "L1"

        def __init__(self):
            self._seen = 0

        def observe(self, iteration):
            self._seen += 1

        def verdict(self) -> LoopVerdict:
            reason = ExitReason.CONTINUE if self._seen < 3 else ExitReason.PLATEAU
            return LoopVerdict(
                exit_reason=reason,
                signals=(
                    LoopSignal(loop_id="L1", name="iterations_seen", value=float(self._seen)),
                ),
                maturity=Maturity.BUILDABLE,
                note="toy monitor, not a real detector",
            )

    monitor = TrivialMonitor()
    assert isinstance(monitor, LoopMonitor)

    for _ in range(5):
        monitor.observe({"diff": "..."})

    v = monitor.verdict()
    assert v.exit_reason is ExitReason.PLATEAU
    assert v.signals[0].value == 5.0
