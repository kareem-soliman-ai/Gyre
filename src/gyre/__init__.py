"""Gyre: psychology-grounded loop patterns for AI agents.

The design in one sentence: a **loop** is a controller and a **measurement** is a
sensor, and Gyre keeps them apart so you can run the same loop with a throwaway
sensor or a validated one and watch it behave differently.

What ships here (all open):
- the measurement seam: ``MeasurementProvider``, ``Measurement``, ``Meaning``
- loop controllers: ``RuminationMonitor`` (L1), ``CalibrationGovernor`` (L2),
  ``EinstellungBreaker`` (L5), ``HabituationFilter`` (L6)
- naive reference providers, so every loop runs out of the box
- ``gyre.bench``: score your own measurement against a baseline
- ``gyre.challenge``: the Alien Factory and objective challenge harnesses

What does not ship here: validated latent-variable measurements. Those take real
psychometric work and live behind a gitignored fence
(``gyre.providers.proprietary``). The naive baselines are honest about being
proxies; build a better one and prove it with ``gyre.bench``.

Read the catalogue: ../loops/INDEX.md
Start the expedition: ../docs/START_HERE.md
Build a measurement: ../docs/building-measurements.md
"""

from gyre.interfaces import (
    ExitReason,
    LoopMonitor,
    LoopVerdict,
    Maturity,
)
from gyre.loops import (
    CalibrationGovernor,
    ChannelObservation,
    EinstellungBreaker,
    HabituationFilter,
    IterationObservation,
    PredictionOutcome,
    ResetDirective,
    RuminationMonitor,
)
from gyre.measurement import Meaning, Measurement, MeasurementProvider

__version__ = "0.2.0"

__all__ = [
    # seam
    "MeasurementProvider",
    "Measurement",
    "Meaning",
    # loop-side interfaces
    "LoopMonitor",
    "LoopVerdict",
    "ExitReason",
    "Maturity",
    # loops
    "RuminationMonitor",
    "IterationObservation",
    "CalibrationGovernor",
    "PredictionOutcome",
    "HabituationFilter",
    "ChannelObservation",
    "EinstellungBreaker",
    "ResetDirective",
    "__version__",
]
