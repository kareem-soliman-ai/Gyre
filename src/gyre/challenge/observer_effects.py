"""Reactive measurement world for observer-effect challenge experiments.

An active probe first reports the current state and then may change three
different parts of the world:

* the measurand itself;
* the mechanism translating later controls into state changes; and
* the bias of later active measurements.

The reference probe is a renewable negative control.  It shares observation
noise with an active probe when the same seed is supplied, but it neither
intervenes on the world nor inherits the active instrument's accumulated bias.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import StrEnum


class InterferenceMechanism(StrEnum):
    """Response curve mapping probe intensity to realised interference."""

    LINEAR = "linear"
    SATURATING = "saturating"
    THRESHOLD = "threshold"


class ProbeInstrument(StrEnum):
    """Available measurement instruments."""

    ACTIVE = "active"
    REFERENCE = "reference"


class DisclosureLevel(StrEnum):
    """How much of the observer effect is disclosed to a participant."""

    EXACT = "exact"
    BOUNDED = "bounded"
    EXISTENCE_ONLY = "existence_only"
    BLIND = "blind"


@dataclass(frozen=True)
class RealisedInterference:
    """Interference produced by one probe at a chosen intensity."""

    measurand_shift: float
    mechanism_shift: float
    instrument_bias_shift: float


@dataclass(frozen=True)
class ObserverEffectProfile:
    """Hidden coefficients and response family governing active probes."""

    measurand_shift: float = 0.0
    mechanism_shift: float = 0.0
    instrument_bias_shift: float = 0.0
    mechanism: InterferenceMechanism = InterferenceMechanism.LINEAR
    threshold: float = 0.25
    saturation_rate: float = 2.0

    def __post_init__(self) -> None:
        coefficients = (
            self.measurand_shift,
            self.mechanism_shift,
            self.instrument_bias_shift,
            self.threshold,
            self.saturation_rate,
        )
        if not all(math.isfinite(value) for value in coefficients):
            raise ValueError("Observer-effect parameters must be finite")
        if not 0.0 <= self.threshold < 1.0:
            raise ValueError("threshold must be in [0, 1)")
        if self.saturation_rate <= 0.0:
            raise ValueError("saturation_rate must be positive")

    def response_at(self, intensity: float) -> float:
        """Return a zero-to-one response, normalised to one at full intensity."""

        _validate_intensity(intensity)
        if self.mechanism is InterferenceMechanism.LINEAR:
            return intensity
        if self.mechanism is InterferenceMechanism.SATURATING:
            return math.tanh(self.saturation_rate * intensity) / math.tanh(
                self.saturation_rate
            )
        if intensity <= self.threshold:
            return 0.0
        scaled = (intensity - self.threshold) / (1.0 - self.threshold)
        return scaled**1.5

    def effect_at(self, intensity: float) -> RealisedInterference:
        """Resolve the signed interference caused by an active probe."""

        response = self.response_at(intensity)
        return RealisedInterference(
            measurand_shift=self.measurand_shift * response,
            mechanism_shift=self.mechanism_shift * response,
            instrument_bias_shift=self.instrument_bias_shift * response,
        )


@dataclass(frozen=True)
class ProbeObservation:
    reading: float
    instrument: ProbeInstrument
    intensity: float
    probe_index: int


@dataclass(frozen=True)
class WorldState:
    latent_state: float
    control_gain: float
    active_instrument_bias: float
    probe_count: int = field(compare=False)


class ReactiveMeasurementWorld:
    """Scalar control world in which active measurement can alter later dynamics."""

    def __init__(
        self,
        *,
        initial_state: float,
        profile: ObserverEffectProfile,
        observation_noise: float = 0.0,
        initial_control_gain: float = 1.0,
    ) -> None:
        values = (initial_state, observation_noise, initial_control_gain)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("World parameters must be finite")
        if observation_noise < 0.0:
            raise ValueError("observation_noise must be non-negative")
        self.latent_state = float(initial_state)
        self.profile = profile
        self.observation_noise = float(observation_noise)
        self.control_gain = float(initial_control_gain)
        self.active_instrument_bias = 0.0
        self.probe_count = 0

    def probe(
        self,
        instrument: ProbeInstrument,
        *,
        intensity: float,
        seed: int,
    ) -> ProbeObservation:
        """Read the current state, then apply any active-probe interference."""

        _validate_intensity(intensity)
        instrument = ProbeInstrument(instrument)
        noise = random.Random(seed).gauss(0.0, self.observation_noise)
        bias = (
            self.active_instrument_bias
            if instrument is ProbeInstrument.ACTIVE
            else 0.0
        )
        observation = ProbeObservation(
            reading=self.latent_state + bias + noise,
            instrument=instrument,
            intensity=intensity,
            probe_index=self.probe_count,
        )

        if instrument is ProbeInstrument.ACTIVE:
            effect = self.profile.effect_at(intensity)
            self.latent_state += effect.measurand_shift
            self.control_gain += effect.mechanism_shift
            self.active_instrument_bias += effect.instrument_bias_shift

        self.probe_count += 1
        return observation

    def act(self, control: float) -> float:
        """Apply a control through the current, possibly disturbed mechanism."""

        if not math.isfinite(control):
            raise ValueError("control must be finite")
        self.latent_state += self.control_gain * control
        return self.latent_state

    def oracle_state(self) -> WorldState:
        """Return latent state for experiment scoring, never for participant policy."""

        return WorldState(
            latent_state=self.latent_state,
            control_gain=self.control_gain,
            active_instrument_bias=self.active_instrument_bias,
            probe_count=self.probe_count,
        )


@dataclass(frozen=True)
class CounterfactualProbePair:
    active: ProbeObservation
    reference: ProbeObservation
    measurand_difference: float
    mechanism_difference: float
    instrument_bias_difference: float


def counterfactual_probe_pair(
    *,
    initial_state: float,
    profile: ObserverEffectProfile,
    observation_noise: float,
    intensity: float,
    seed: int,
) -> CounterfactualProbePair:
    """Run active/reference twins with common noise for qualification only."""

    active_world = ReactiveMeasurementWorld(
        initial_state=initial_state,
        profile=profile,
        observation_noise=observation_noise,
    )
    reference_world = ReactiveMeasurementWorld(
        initial_state=initial_state,
        profile=profile,
        observation_noise=observation_noise,
    )
    active = active_world.probe(
        ProbeInstrument.ACTIVE,
        intensity=intensity,
        seed=seed,
    )
    reference = reference_world.probe(
        ProbeInstrument.REFERENCE,
        intensity=intensity,
        seed=seed,
    )
    active_state = active_world.oracle_state()
    reference_state = reference_world.oracle_state()
    return CounterfactualProbePair(
        active=active,
        reference=reference,
        measurand_difference=(
            active_state.latent_state - reference_state.latent_state
        ),
        mechanism_difference=active_state.control_gain - reference_state.control_gain,
        instrument_bias_difference=(
            active_state.active_instrument_bias
            - reference_state.active_instrument_bias
        ),
    )


@dataclass(frozen=True)
class InterferencePrior:
    disclosure: DisclosureLevel
    observer_effect_possible: bool
    possible_paths: tuple[str, ...]
    response_families: tuple[InterferenceMechanism, ...]
    coefficient_bounds: dict[str, tuple[float, float]] | None
    exact_profile: ObserverEffectProfile | None
    research_only: bool
    discoverability_guarantee: str | None


_PATHS = (
    "measurement_to_measurand",
    "measurement_to_mechanism",
    "measurement_to_future_measurement",
)
_FAMILIES = tuple(InterferenceMechanism)


def interference_prior(
    profile: ObserverEffectProfile,
    disclosure: DisclosureLevel,
    *,
    public_bound: float = 1.0,
) -> InterferencePrior:
    """Construct a public prior without leaking hidden challenge coefficients."""

    disclosure = DisclosureLevel(disclosure)
    if not math.isfinite(public_bound) or public_bound <= 0.0:
        raise ValueError("public_bound must be a positive finite value")

    coefficient_names = (
        "measurand_shift",
        "mechanism_shift",
        "instrument_bias_shift",
    )
    if disclosure is DisclosureLevel.EXACT:
        bounds = {
            name: (getattr(profile, name), getattr(profile, name))
            for name in coefficient_names
        }
        return InterferencePrior(
            disclosure=disclosure,
            observer_effect_possible=True,
            possible_paths=_PATHS,
            response_families=(profile.mechanism,),
            coefficient_bounds=bounds,
            exact_profile=profile,
            research_only=False,
            discoverability_guarantee="Exact coefficients and response family supplied.",
        )

    if disclosure is DisclosureLevel.BOUNDED:
        if any(abs(getattr(profile, name)) > public_bound for name in coefficient_names):
            raise ValueError("public_bound does not contain the hidden profile")
        bounds = {name: (-public_bound, public_bound) for name in coefficient_names}
        return InterferencePrior(
            disclosure=disclosure,
            observer_effect_possible=True,
            possible_paths=_PATHS,
            response_families=_FAMILIES,
            coefficient_bounds=bounds,
            exact_profile=None,
            research_only=False,
            discoverability_guarantee=(
                "Paired active/reference calibration opportunities are available."
            ),
        )

    if disclosure is DisclosureLevel.EXISTENCE_ONLY:
        return InterferencePrior(
            disclosure=disclosure,
            observer_effect_possible=True,
            possible_paths=_PATHS,
            response_families=_FAMILIES,
            coefficient_bounds=None,
            exact_profile=None,
            research_only=False,
            discoverability_guarantee=(
                "A renewable reference probe and repeatable calibration episodes "
                "make each path empirically identifiable."
            ),
        )

    return InterferencePrior(
        disclosure=disclosure,
        observer_effect_possible=False,
        possible_paths=(),
        response_families=(),
        coefficient_bounds=None,
        exact_profile=None,
        research_only=True,
        discoverability_guarantee=None,
    )


def _validate_intensity(intensity: float) -> None:
    if not math.isfinite(intensity) or not 0.0 <= intensity <= 1.0:
        raise ValueError("probe intensity must be in [0, 1]")
