"""Gyre: psychology-grounded loop patterns for AI agents.

This v0.1 package ships *interfaces and vocabulary*, not detectors. It gives you
the types to write your own loop monitors against a common shape while the
measurement instruments (see docs/measurement-stance.md) mature.

Nothing here scores anything. There are no thresholds, no validated detectors,
and deliberately so: a detector that makes a confident claim it has not earned is
a liability, not a contribution. What this package gives you is the *shape* every
loop monitor in the catalogue shares, so that when you build the L1 rumination
detector or the L6 habituation filter, it plugs into the same interface as
everyone else's.

Read the catalogue first: ../loops/INDEX.md
"""

from gyre.interfaces import (
    ExitReason,
    LoopMonitor,
    LoopSignal,
    LoopVerdict,
    Maturity,
)

__version__ = "0.1.0"

__all__ = [
    "ExitReason",
    "LoopMonitor",
    "LoopSignal",
    "LoopVerdict",
    "Maturity",
    "__version__",
]
