"""Loop controllers. Each is measurement-agnostic: construct it with a provider.

- L1 RuminationMonitor   — is the loop still generating information?
- L2 CalibrationGovernor — does the agent's confidence track its accuracy?
- L5 EinstellungBreaker  — on a plateau, reset or escalate? (a policy, not a monitor)
- L6 HabituationFilter   — has a channel deviated from its learned baseline?

See ../../loops/INDEX.md for the psychology behind each.
"""

from gyre.loops.calibration import CalibrationGovernor, PredictionOutcome
from gyre.loops.habituation import ChannelObservation, HabituationFilter
from gyre.loops.incubation import EinstellungBreaker, ResetDirective
from gyre.loops.rumination import IterationObservation, RuminationMonitor

__all__ = [
    "RuminationMonitor",
    "IterationObservation",
    "CalibrationGovernor",
    "PredictionOutcome",
    "HabituationFilter",
    "ChannelObservation",
    "EinstellungBreaker",
    "ResetDirective",
]
