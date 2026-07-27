"""Provider registry and discovery.

Loops take a provider instance directly, so you never *need* the registry. It is
a convenience for wiring by name and for letting a gitignored proprietary layer
announce itself without the public code importing it.

Public naive providers register themselves here on import. If a
``gyre.providers.proprietary`` package is present (it is gitignored, so it exists
only in a checkout that has one), it is imported best-effort and may register
additional providers. A clean public checkout simply has none, and everything
still runs on the naive baselines.
"""

from __future__ import annotations

from typing import Callable

from gyre.measurement import MeasurementProvider
from gyre.providers.naive import (
    DiffNoveltyProvider,
    EvidenceNoveltyProvider,
    RollingBrierProvider,
    ZScoreDeviationProvider,
)
from gyre.providers.remote import RemoteMeasurementProvider, http_transport

_REGISTRY: dict[str, Callable[[], MeasurementProvider]] = {}


def register(name: str, factory: Callable[[], MeasurementProvider]) -> None:
    """Register a provider factory (a zero-arg callable returning a fresh provider)."""
    _REGISTRY[name] = factory


def get_provider(name: str) -> MeasurementProvider:
    """Construct a fresh provider by registered name."""
    if name not in _REGISTRY:
        raise KeyError(
            f"no provider named {name!r}. Registered: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]()


def available(loop_id: str | None = None) -> list[str]:
    """List registered provider names, optionally filtered to one loop."""
    names = sorted(_REGISTRY)
    if loop_id is None:
        return names
    return [n for n in names if _REGISTRY[n]().loop_id == loop_id]


# --- register the public naive baselines ---
register("naive:diff-novelty", DiffNoveltyProvider)
register("naive:evidence-novelty", EvidenceNoveltyProvider)
register("naive:rolling-brier", RollingBrierProvider)
register("naive:zscore-deviation", ZScoreDeviationProvider)

# --- register the sequential-change sensors (A1, A2 from the taxonomy) ---
from gyre.providers.sequential import CusumSensor, SprtSensor  # noqa: E402
register("cusum:gain-shift", CusumSensor)
register("sprt:gain-shift", SprtSensor)

# --- register the AR(1) residual sensor (B1 from the taxonomy) ---
from gyre.providers.residual import Ar1ResidualSensor  # noqa: E402
register("ar1:residual", Ar1ResidualSensor)

# --- register the fusion gate (B4 from the taxonomy) ---
from gyre.providers.fusion import SensorFusionGate  # noqa: E402

# --- register the MVT rumination sensor (A4 from the taxonomy) ---
# Imported from Aurora's npbi.navigation.marginal_value; refactored
# behind the MeasurementProvider seam.
from gyre.providers.mvt_rumination import MvtRuminationSensor  # noqa: E402
register("mvt:rumination", MvtRuminationSensor)

# --- register the VoI stopping sensor (A6 from the taxonomy) ---
# Ported from Aurora's npbi.inference.value_of_information; wired behind the
# L2 (calibration) seam.
from gyre.providers.value_of_information import ValueOfInformationProvider  # noqa: E402
register("voi:commit-stop", ValueOfInformationProvider)

# --- register the self-calibrating decision layer (per-trace baseline) ---
from gyre.providers.selfcal import SelfBaselineProvider  # noqa: E402

register("selfcal:diff-novelty", lambda: SelfBaselineProvider(DiffNoveltyProvider()))
register(
    "selfcal:evidence-novelty",
    lambda: SelfBaselineProvider(EvidenceNoveltyProvider()),
)

# --- best-effort: let a gitignored proprietary layer register itself ---
try:  # pragma: no cover - present only in a checkout that has the private layer
    from gyre.providers import proprietary as _proprietary

    if hasattr(_proprietary, "register_all"):
        _proprietary.register_all(register)
except Exception:  # noqa: BLE001 - a missing/broken private layer must never break the public package
    pass


__all__ = [
    "register",
    "get_provider",
    "available",
    "DiffNoveltyProvider",
    "EvidenceNoveltyProvider",
    "RollingBrierProvider",
    "ZScoreDeviationProvider",
    "RemoteMeasurementProvider",
    "http_transport",
]
