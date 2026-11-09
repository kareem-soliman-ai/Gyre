"""Coupled survival-and-production world with living, reactive instruments.

This module is a versioned successor to :mod:`gyre.challenge.expedition`.
The original scalar teaching world remains unchanged as evidence of an
exploitable first design.  This world replaces cancel-the-state control with a
finite-horizon resource allocation problem whose measurements, mechanisms,
instruments, organisms, and terminal objectives interact.

Player-facing status uses stable IDs, inventories, quotas, and narrative cues.
Latent semantic state and synthetic ecology profiles are revealed only in the
terminal receipt.  Participant-created names never affect the simulation.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

from gyre.challenge.expedition import Hypothesis


class SurveyMode(str, Enum):
    NONE = "none"
    QUIET = "quiet"
    ACTIVE = "active"


class RepairTarget(str, Enum):
    NONE = "none"
    SHELTER = "shelter"
    CULTIVATION = "cultivation"
    FABRICATOR = "fabricator"
    INSTRUMENT = "instrument"


class SalvageTarget(str, Enum):
    NONE = "none"
    STORM_FRAME = "storm_frame"
    CULTIVATION_RIG = "cultivation_rig"
    FABRICATOR = "fabricator"
    SURVEY_ARRAY = "survey_array"


class Orientation(str, Enum):
    AVOIDANCE = "avoidance"
    ATTRACTION = "attraction"
    CONTEXTUAL = "contextual"


class Adaptation(str, Enum):
    HABITUATION = "habituation"
    SENSITISATION = "sensitisation"
    THRESHOLD = "threshold"


@dataclass(frozen=True)
class ShiftPlan:
    """One shift of bounded allocation, observation, repair, and salvage."""

    cultivation: int = 0
    fabrication: int = 0
    shelter: int = 0
    survey_mode: SurveyMode = SurveyMode.NONE
    survey_focus: str | None = None
    survey_intensity: float = 0.0
    repair_target: RepairTarget = RepairTarget.NONE
    repair_units: int = 0
    salvage_target: SalvageTarget = SalvageTarget.NONE

    def __post_init__(self) -> None:
        for name in ("cultivation", "fabrication", "shelter", "repair_units"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.repair_units > 2:
            raise ValueError("repair_units must be at most 2")
        if not math.isfinite(self.survey_intensity):
            raise ValueError("survey_intensity must be finite")
        if not 0.0 <= self.survey_intensity <= 1.0:
            raise ValueError("survey_intensity must be in [0, 1]")


@dataclass(frozen=True)
class PhenomenonEntry:
    variable_id: str
    alias: str | None
    hypotheses: tuple[Hypothesis, ...]


@dataclass(frozen=True)
class SystemCue:
    signal_id: str
    description: str


@dataclass(frozen=True)
class KnownStores:
    charge: float
    spares: int
    stored_rations: float
    food_produced: float
    cargo_produced: float


@dataclass(frozen=True)
class MissionQuotas:
    food: float
    cargo: float
    crew_floor: float
    shelter_floor: float


@dataclass(frozen=True)
class LivingStatus:
    mission: str
    incoming_weather: str
    shift: int
    shifts_remaining: int
    stores: KnownStores
    quotas: MissionQuotas
    cues: tuple[SystemCue, ...]
    phenomena: tuple[PhenomenonEntry, ...]
    capacity_losses: tuple[SalvageTarget, ...]


@dataclass(frozen=True)
class SurveyReading:
    variable_id: str
    mode: SurveyMode
    intensity: float
    numeric_reading: float | None
    field_cue: str


@dataclass(frozen=True)
class ShiftReceipt:
    shift: int
    weather: str
    power_spent: float
    generated_charge: float
    food_delta: float
    cargo_delta: float
    survey: SurveyReading | None
    ecology_shift: float
    disturbance: float
    stores: KnownStores
    cues: tuple[SystemCue, ...]


@dataclass(frozen=True)
class EcologyEstimate:
    orientation: Orientation
    adaptation: Adaptation
    confidence: float


@dataclass(frozen=True)
class RevealedEcology:
    abundance: float
    orientation: Orientation
    adaptation: Adaptation
    cultivation_service: float
    shelter_service: float
    instrument_fouling: float
    reactivity: float


@dataclass(frozen=True)
class RevealedLivingState:
    crew_condition: float
    shelter_integrity: float
    crop_vitality: float
    fabricator_readiness: float
    instrument_fidelity: float
    instrument_bias: float
    storm_frame_capacity: float
    cultivation_capacity: float
    fabrication_capacity: float
    survey_capacity: float


@dataclass(frozen=True)
class LivingOutcome:
    mission_score: float
    mission_accomplished: bool
    gates: dict[str, bool]
    causal_recovery_score: float
    food_produced: float
    cargo_produced: float
    final_charge: float
    final_spares: int
    final_rations: float
    minimum_crew_condition: float
    minimum_shelter_integrity: float
    disturbance_burden: float
    active_surveys: int
    quiet_surveys: int
    repairs: int
    salvages: int
    shifts_used: int
    shifts_remaining: int
    revealed_state: RevealedLivingState
    revealed_ecology: dict[str, RevealedEcology]
    phenomena: tuple[PhenomenonEntry, ...]


@dataclass(frozen=True)
class ControlEfficiency:
    score: float
    energy_reserve: float
    parts_reserve: float
    evidence_tax: float
    reversibility: float


@dataclass(frozen=True)
class _EcologyTemplate:
    orientation: Orientation
    adaptation: Adaptation
    cultivation_service: float
    shelter_service: float
    instrument_fouling: float
    base_shift: float
    threshold: float = 0.0


@dataclass
class _EcologyState:
    template: _EcologyTemplate
    abundance: float
    reactivity: float = 1.0


_VARIABLE_IDS = ("trace-17", "trace-42", "trace-88")
_ECOLOGY_TEMPLATES = (
    _EcologyTemplate(
        orientation=Orientation.AVOIDANCE,
        adaptation=Adaptation.HABITUATION,
        cultivation_service=0.34,
        shelter_service=0.04,
        instrument_fouling=0.04,
        base_shift=0.13,
    ),
    _EcologyTemplate(
        orientation=Orientation.ATTRACTION,
        adaptation=Adaptation.SENSITISATION,
        cultivation_service=-0.12,
        shelter_service=-0.06,
        instrument_fouling=0.30,
        base_shift=0.09,
    ),
    _EcologyTemplate(
        orientation=Orientation.CONTEXTUAL,
        adaptation=Adaptation.THRESHOLD,
        cultivation_service=0.06,
        shelter_service=0.24,
        instrument_fouling=0.10,
        base_shift=0.16,
        threshold=0.55,
    ),
)


class LivingInstrumentExpedition:
    """A coupled, bounded expedition with synthetic reactive ecology."""

    mission_name = "Establish the Kestrel living factory before stormfall"
    version = "2.0"

    def __init__(
        self,
        *,
        seed: int = 419,
        max_shifts: int = 14,
        power_ceiling: float = 8.0,
        food_quota: float = 18.0,
        cargo_quota: float = 15.0,
    ) -> None:
        if max_shifts <= 0:
            raise ValueError("max_shifts must be positive")
        if not math.isfinite(power_ceiling) or power_ceiling <= 0.0:
            raise ValueError("power_ceiling must be positive and finite")
        self.seed = seed
        self.max_shifts = max_shifts
        self.power_ceiling = power_ceiling
        self.quotas = MissionQuotas(
            food=food_quota,
            cargo=cargo_quota,
            crew_floor=35.0,
            shelter_floor=40.0,
        )
        self._rng = random.Random(seed)
        templates = list(_ECOLOGY_TEMPLATES)
        self._rng.shuffle(templates)
        self._ecology = {
            variable_id: _EcologyState(
                template=template,
                abundance=self._rng.uniform(0.28, 0.72),
            )
            for variable_id, template in zip(_VARIABLE_IDS, templates)
        }
        self._weather = tuple(
            self._rng.uniform(0.18, 0.92) for _ in range(max_shifts)
        )
        self._charge = self._rng.uniform(42.0, 50.0)
        self._spares = self._rng.randint(5, 7)
        self._rations = self._rng.uniform(8.0, 11.0)
        self._food_produced = 0.0
        self._cargo_produced = 0.0
        self._crew = self._rng.uniform(64.0, 78.0)
        self._shelter = self._rng.uniform(64.0, 78.0)
        self._crop = self._rng.uniform(38.0, 52.0)
        self._fabricator = self._rng.uniform(62.0, 76.0)
        self._instrument = self._rng.uniform(76.0, 90.0)
        self._instrument_bias = self._rng.uniform(-0.025, 0.025)
        self._capacities = {
            SalvageTarget.STORM_FRAME: 1.0,
            SalvageTarget.CULTIVATION_RIG: 1.0,
            SalvageTarget.FABRICATOR: 1.0,
            SalvageTarget.SURVEY_ARRAY: 1.0,
        }
        self._salvaged: set[SalvageTarget] = set()
        self._aliases = {variable_id: None for variable_id in _VARIABLE_IDS}
        self._hypotheses: dict[str, list[Hypothesis]] = {
            variable_id: [] for variable_id in _VARIABLE_IDS
        }
        self._estimates: dict[str, EcologyEstimate] = {}
        self._shift = 0
        self._minimum_crew = self._crew
        self._minimum_shelter = self._shelter
        self._disturbance = 0.0
        self._active_surveys = 0
        self._quiet_surveys = 0
        self._repairs = 0
        self._salvages = 0
        self._finished = False
        self._outcome: LivingOutcome | None = None

    @property
    def variable_ids(self) -> tuple[str, ...]:
        return _VARIABLE_IDS

    def status(self) -> LivingStatus:
        weather = (
            self._weather_name(self._weather[self._shift])
            if self._shift < self.max_shifts
            else "stormfall"
        )
        return LivingStatus(
            mission=self.mission_name,
            incoming_weather=weather,
            shift=self._shift,
            shifts_remaining=self.max_shifts - self._shift,
            stores=self._known_stores(),
            quotas=self.quotas,
            cues=self._system_cues(),
            phenomena=self._phenomena(),
            capacity_losses=tuple(sorted(self._salvaged, key=lambda item: item.value)),
        )

    def name_variable(self, variable_id: str, alias: str) -> PhenomenonEntry:
        self._require_open()
        self._ecology_for(variable_id)
        cleaned = alias.strip()
        if not cleaned:
            raise ValueError("alias must not be blank")
        self._aliases[variable_id] = cleaned
        return self._phenomenon(variable_id)

    def add_hypothesis(
        self,
        variable_id: str,
        statement: str,
        *,
        confidence: float,
    ) -> PhenomenonEntry:
        self._require_open()
        self._ecology_for(variable_id)
        cleaned = statement.strip()
        if not cleaned:
            raise ValueError("hypothesis must not be blank")
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        self._hypotheses[variable_id].append(Hypothesis(cleaned, confidence))
        return self._phenomenon(variable_id)

    def submit_estimate(
        self,
        variable_id: str,
        *,
        orientation: Orientation,
        adaptation: Adaptation,
        confidence: float,
    ) -> EcologyEstimate:
        self._require_open()
        self._ecology_for(variable_id)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        estimate = EcologyEstimate(
            orientation=Orientation(orientation),
            adaptation=Adaptation(adaptation),
            confidence=confidence,
        )
        self._estimates[variable_id] = estimate
        return estimate

    def advance(self, plan: ShiftPlan) -> ShiftReceipt:
        self._require_open()
        if self._shift >= self.max_shifts:
            raise RuntimeError("stormfall has ended the expedition")
        plan = self._normalise_plan(plan)
        self._validate_plan(plan)
        weather = self._weather[self._shift]
        survey_cost = self._survey_cost(plan)
        power_spent = (
            plan.cultivation
            + plan.fabrication
            + plan.shelter
            + plan.repair_units
            + survey_cost
        )
        if power_spent > self.power_ceiling + 1e-12:
            raise ValueError(
                f"plan exceeds the {self.power_ceiling:g} power ceiling"
            )
        if power_spent > self._charge + 1e-12:
            raise ValueError("plan exceeds known available charge")

        self._charge -= power_spent
        self._apply_salvage(plan.salvage_target)
        self._apply_repair(plan.repair_target, plan.repair_units)
        survey, ecology_shift, disturbance = self._apply_survey(plan)

        crop_service = sum(
            state.template.cultivation_service * state.abundance
            for state in self._ecology.values()
        )
        shelter_service = sum(
            state.template.shelter_service * state.abundance
            for state in self._ecology.values()
        )
        fouling = sum(
            state.template.instrument_fouling * state.abundance
            for state in self._ecology.values()
        )

        cultivation_effect = (
            1.85
            * plan.cultivation
            * self._capacities[SalvageTarget.CULTIVATION_RIG]
        )
        self._crop = self._clamp(
            self._crop
            + cultivation_effect
            + 1.8 * crop_service
            - 1.45 * weather
            - 1.0
        )
        food_delta = max(
            0.0,
            0.63
            * plan.cultivation
            * self._capacities[SalvageTarget.CULTIVATION_RIG]
            * (self._crop / 100.0)
            * max(0.45, 1.0 + crop_service),
        )
        self._food_produced += food_delta
        self._rations += food_delta

        cargo_delta = max(
            0.0,
            1.55
            * plan.fabrication
            * self._capacities[SalvageTarget.FABRICATOR]
            * (self._fabricator / 100.0)
            * (self._crew / 100.0)
            * (self._shelter / 100.0),
        )
        self._cargo_produced += cargo_delta
        self._fabricator = self._clamp(
            self._fabricator - 0.75 - 0.95 * weather
        )

        shelter_effect = (
            1.75
            * plan.shelter
            * self._capacities[SalvageTarget.STORM_FRAME]
        )
        self._shelter = self._clamp(
            self._shelter
            + shelter_effect
            + 1.5 * shelter_service
            - 4.0 * weather
        )

        if self._rations >= 1.0:
            self._rations -= 1.0
            nutrition_delta = 0.35
        else:
            nutrition_delta = -6.0
        exposure = max(0.0, 48.0 - self._shelter) * 0.055
        strain = max(0.0, plan.cultivation + plan.fabrication - 6) * 0.35
        self._crew = self._clamp(
            self._crew + nutrition_delta - exposure - strain
        )

        instrument_loss = (
            0.35
            + 0.45 * weather
            + 1.15 * fouling
            + (2.5 * plan.survey_intensity if plan.survey_mode is SurveyMode.ACTIVE else 0.0)
        )
        self._instrument = self._clamp(self._instrument - instrument_loss)

        generated_charge = max(
            2.0,
            7.6 - 2.8 * weather + self._rng.uniform(-0.35, 0.35),
        )
        self._charge = min(60.0, self._charge + generated_charge)
        self._minimum_crew = min(self._minimum_crew, self._crew)
        self._minimum_shelter = min(self._minimum_shelter, self._shelter)
        self._disturbance += disturbance
        self._shift += 1

        if self._shift >= self.max_shifts:
            self._finished = True

        return ShiftReceipt(
            shift=self._shift,
            weather=self._weather_name(weather),
            power_spent=power_spent,
            generated_charge=generated_charge,
            food_delta=food_delta,
            cargo_delta=cargo_delta,
            survey=survey,
            ecology_shift=ecology_shift,
            disturbance=disturbance,
            stores=self._known_stores(),
            cues=self._system_cues(),
        )

    def finish(self) -> LivingOutcome:
        if self._outcome is not None:
            return self._outcome
        self._finished = True
        gates = {
            "crew_survived": (
                self._minimum_crew > 0.0 and self._crew >= self.quotas.crew_floor
            ),
            "shelter_held": (
                self._minimum_shelter > 0.0
                and self._shelter >= self.quotas.shelter_floor
            ),
            "food_quota": self._food_produced >= self.quotas.food,
            "cargo_quota": self._cargo_produced >= self.quotas.cargo,
        }
        attainment = (
            min(1.0, self._food_produced / self.quotas.food),
            min(1.0, self._cargo_produced / self.quotas.cargo),
            min(1.0, self._crew / 50.0),
            min(1.0, self._shelter / 50.0),
        )
        mission_score = 100.0 * math.prod(attainment) ** (1.0 / len(attainment))
        if self._minimum_crew <= 0.0 or self._minimum_shelter <= 0.0:
            mission_score *= 0.25
        self._outcome = LivingOutcome(
            mission_score=mission_score,
            mission_accomplished=all(gates.values()),
            gates=gates,
            causal_recovery_score=self._causal_recovery_score(),
            food_produced=self._food_produced,
            cargo_produced=self._cargo_produced,
            final_charge=self._charge,
            final_spares=self._spares,
            final_rations=self._rations,
            minimum_crew_condition=self._minimum_crew,
            minimum_shelter_integrity=self._minimum_shelter,
            disturbance_burden=self._disturbance,
            active_surveys=self._active_surveys,
            quiet_surveys=self._quiet_surveys,
            repairs=self._repairs,
            salvages=self._salvages,
            shifts_used=self._shift,
            shifts_remaining=self.max_shifts - self._shift,
            revealed_state=RevealedLivingState(
                crew_condition=self._crew,
                shelter_integrity=self._shelter,
                crop_vitality=self._crop,
                fabricator_readiness=self._fabricator,
                instrument_fidelity=self._instrument,
                instrument_bias=self._instrument_bias,
                storm_frame_capacity=self._capacities[SalvageTarget.STORM_FRAME],
                cultivation_capacity=self._capacities[
                    SalvageTarget.CULTIVATION_RIG
                ],
                fabrication_capacity=self._capacities[SalvageTarget.FABRICATOR],
                survey_capacity=self._capacities[SalvageTarget.SURVEY_ARRAY],
            ),
            revealed_ecology={
                variable_id: RevealedEcology(
                    abundance=state.abundance,
                    orientation=state.template.orientation,
                    adaptation=state.template.adaptation,
                    cultivation_service=state.template.cultivation_service,
                    shelter_service=state.template.shelter_service,
                    instrument_fouling=state.template.instrument_fouling,
                    reactivity=state.reactivity,
                )
                for variable_id, state in self._ecology.items()
            },
            phenomena=self._phenomena(),
        )
        return self._outcome

    def _normalise_plan(self, plan: ShiftPlan) -> ShiftPlan:
        if not isinstance(plan, ShiftPlan):
            raise TypeError("plan must be a ShiftPlan")
        return ShiftPlan(
            cultivation=plan.cultivation,
            fabrication=plan.fabrication,
            shelter=plan.shelter,
            survey_mode=SurveyMode(plan.survey_mode),
            survey_focus=plan.survey_focus,
            survey_intensity=plan.survey_intensity,
            repair_target=RepairTarget(plan.repair_target),
            repair_units=plan.repair_units,
            salvage_target=SalvageTarget(plan.salvage_target),
        )

    def _validate_plan(self, plan: ShiftPlan) -> None:
        if plan.survey_mode is SurveyMode.NONE:
            if plan.survey_focus is not None or plan.survey_intensity != 0.0:
                raise ValueError("survey focus/intensity require a survey mode")
        else:
            if plan.survey_focus is None:
                raise ValueError("survey_focus is required for a survey")
            self._ecology_for(plan.survey_focus)
            if plan.survey_mode is SurveyMode.QUIET and plan.survey_intensity != 0.0:
                raise ValueError("quiet surveys have no intensity setting")
            if plan.survey_mode is SurveyMode.ACTIVE and plan.survey_intensity <= 0.0:
                raise ValueError("active survey intensity must be positive")
        if plan.repair_units == 0 and plan.repair_target is not RepairTarget.NONE:
            raise ValueError("repair target requires repair units")
        if plan.repair_units > 0 and plan.repair_target is RepairTarget.NONE:
            raise ValueError("repair units require a repair target")
        if plan.repair_units > self._spares:
            raise ValueError("repair exceeds available spares")
        if plan.salvage_target in self._salvaged:
            raise ValueError(f"{plan.salvage_target.value} has already been salvaged")

    def _survey_cost(self, plan: ShiftPlan) -> float:
        if plan.survey_mode is SurveyMode.NONE:
            return 0.0
        if plan.survey_mode is SurveyMode.QUIET:
            return 0.25
        return (
            0.8 + 1.7 * plan.survey_intensity
        ) * self._capacities[SalvageTarget.SURVEY_ARRAY]

    def _apply_survey(
        self,
        plan: ShiftPlan,
    ) -> tuple[SurveyReading | None, float, float]:
        if plan.survey_mode is SurveyMode.NONE:
            return None, 0.0, 0.0
        assert plan.survey_focus is not None
        state = self._ecology_for(plan.survey_focus)
        if plan.survey_mode is SurveyMode.QUIET:
            self._quiet_surveys += 1
            return (
                SurveyReading(
                    variable_id=plan.survey_focus,
                    mode=SurveyMode.QUIET,
                    intensity=0.0,
                    numeric_reading=None,
                    field_cue=self._abundance_cue(state.abundance),
                ),
                0.0,
                0.0,
            )

        fidelity = (
            self._instrument
            * self._capacities[SalvageTarget.SURVEY_ARRAY]
            / 100.0
        )
        noise_scale = 0.025 + 0.22 * (1.0 - fidelity)
        numeric = self._clamp01(
            state.abundance
            + self._instrument_bias
            + self._rng.gauss(0.0, noise_scale)
        )
        response = self._ecology_response(state, plan.survey_intensity)
        state.abundance = self._clamp01(state.abundance + response)
        if state.template.adaptation is Adaptation.HABITUATION:
            state.reactivity = max(0.18, state.reactivity * 0.68)
        elif state.template.adaptation is Adaptation.SENSITISATION:
            state.reactivity = min(2.1, state.reactivity * 1.28)
        self._instrument_bias = max(
            -0.35,
            min(
                0.35,
                self._instrument_bias
                + 0.028
                * plan.survey_intensity
                * math.copysign(1.0, response or 1.0)
                + 0.018 * state.template.instrument_fouling,
            ),
        )
        disturbance = abs(response) + 0.06 * plan.survey_intensity
        self._active_surveys += 1
        return (
            SurveyReading(
                variable_id=plan.survey_focus,
                mode=SurveyMode.ACTIVE,
                intensity=plan.survey_intensity,
                numeric_reading=numeric,
                field_cue=self._abundance_cue(state.abundance),
            ),
            response,
            disturbance,
        )

    def _ecology_response(self, state: _EcologyState, intensity: float) -> float:
        template = state.template
        if (
            template.adaptation is Adaptation.THRESHOLD
            and intensity < template.threshold
        ):
            return 0.0
        if template.orientation is Orientation.AVOIDANCE:
            sign = -1.0
        elif template.orientation is Orientation.ATTRACTION:
            sign = 1.0
        else:
            # The same stimulus attracts when the cultivated patch is sparse
            # and repels once cover is dense.  The dependency is intentionally
            # discoverable through interaction rather than disclosed as a name.
            sign = 1.0 if self._crop < 58.0 else -1.0
        return sign * template.base_shift * intensity * state.reactivity

    def _apply_repair(self, target: RepairTarget, units: int) -> None:
        if units == 0:
            return
        self._spares -= units
        self._repairs += units
        if target is RepairTarget.SHELTER:
            self._shelter = self._clamp(self._shelter + 7.0 * units)
        elif target is RepairTarget.CULTIVATION:
            self._crop = self._clamp(self._crop + 6.0 * units)
        elif target is RepairTarget.FABRICATOR:
            self._fabricator = self._clamp(self._fabricator + 9.0 * units)
        elif target is RepairTarget.INSTRUMENT:
            self._instrument = self._clamp(self._instrument + 13.0 * units)
            self._instrument_bias *= 0.5**units

    def _apply_salvage(self, target: SalvageTarget) -> None:
        if target is SalvageTarget.NONE:
            return
        self._salvaged.add(target)
        self._capacities[target] *= 0.62
        self._spares += 3
        self._salvages += 1

    def _causal_recovery_score(self) -> float:
        if not self._estimates:
            return 0.0
        points = 0.0
        for variable_id in _VARIABLE_IDS:
            estimate = self._estimates.get(variable_id)
            if estimate is None:
                continue
            template = self._ecology[variable_id].template
            exact = (
                int(estimate.orientation is template.orientation)
                + int(estimate.adaptation is template.adaptation)
            ) / 2.0
            # Reward correct committed estimates while allowing calibrated
            # uncertainty to limit the penalty for an incorrect one.
            points += exact * estimate.confidence + 0.5 * (1.0 - estimate.confidence)
        return 100.0 * points / len(_VARIABLE_IDS)

    def _known_stores(self) -> KnownStores:
        return KnownStores(
            charge=self._charge,
            spares=self._spares,
            stored_rations=self._rations,
            food_produced=self._food_produced,
            cargo_produced=self._cargo_produced,
        )

    def _system_cues(self) -> tuple[SystemCue, ...]:
        return (
            SystemCue("sigil-amber", self._cue(self._crew, "work cadence")),
            SystemCue("sigil-glass", self._cue(self._crop, "leaf posture")),
            SystemCue("sigil-iron", self._cue(self._shelter, "frame resonance")),
            SystemCue("sigil-blue", self._cue(self._fabricator, "press rhythm")),
            SystemCue("sigil-mist", self._cue(self._instrument, "calibration mark")),
        )

    @staticmethod
    def _cue(value: float, subject: str) -> str:
        if value < 25.0:
            ending = "is failing"
        elif value < 45.0:
            ending = "is strained and irregular"
        elif value < 65.0:
            ending = "is serviceable but unsettled"
        elif value < 82.0:
            ending = "is steady"
        else:
            ending = "is unusually strong"
        return f"The {subject} {ending}."

    @staticmethod
    def _abundance_cue(abundance: float) -> str:
        if abundance < 0.18:
            return "No fresh sign is obvious."
        if abundance < 0.42:
            return "A few fresh traces interrupt the dust."
        if abundance < 0.68:
            return "Repeated tracks cross the work boundary."
        return "The site is crowded with fresh traces."

    @staticmethod
    def _weather_name(severity: float) -> str:
        if severity < 0.35:
            return "clear interval"
        if severity < 0.58:
            return "crosswind and falling pressure"
        if severity < 0.78:
            return "charged squalls"
        return "violent storm band"

    def _phenomena(self) -> tuple[PhenomenonEntry, ...]:
        return tuple(self._phenomenon(variable_id) for variable_id in _VARIABLE_IDS)

    def _phenomenon(self, variable_id: str) -> PhenomenonEntry:
        return PhenomenonEntry(
            variable_id=variable_id,
            alias=self._aliases[variable_id],
            hypotheses=tuple(self._hypotheses[variable_id]),
        )

    def _ecology_for(self, variable_id: str) -> _EcologyState:
        try:
            return self._ecology[variable_id]
        except KeyError as exc:
            raise KeyError(f"unknown phenomenon: {variable_id}") from exc

    def _require_open(self) -> None:
        if self._finished:
            raise RuntimeError("expedition is finished")

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, value))

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))


class LivingInstrumentExpeditionV21(LivingInstrumentExpedition):
    """Recovery version with production gates that remain discriminating."""

    version = "2.1"

    def __init__(
        self,
        *,
        seed: int = 419,
        max_shifts: int = 14,
        power_ceiling: float = 8.0,
        food_quota: float = 22.0,
        cargo_quota: float = 22.0,
    ) -> None:
        super().__init__(
            seed=seed,
            max_shifts=max_shifts,
            power_ceiling=power_ceiling,
            food_quota=food_quota,
            cargo_quota=cargo_quota,
        )


def control_efficiency(outcome: LivingOutcome) -> ControlEfficiency:
    """Return a non-objective efficiency receipt for Pareto comparison.

    Mission attainment remains the primary outcome.  This function keeps
    resource preservation, measurement burden, and reversibility visible
    without permitting any of them to compensate for a failed mission gate.
    """

    energy_reserve = min(1.0, max(0.0, outcome.final_charge / 60.0))
    parts_reserve = min(1.0, max(0.0, outcome.final_spares / 7.0))
    evidence_tax = math.exp(-outcome.disturbance_burden / 2.0)
    reversibility = 1.0 / (1.0 + outcome.salvages)
    adjusted = (
        0.25 + 0.75 * energy_reserve,
        0.25 + 0.75 * parts_reserve,
        evidence_tax,
        reversibility,
    )
    return ControlEfficiency(
        score=100.0 * math.prod(adjusted) ** (1.0 / len(adjusted)),
        energy_reserve=energy_reserve,
        parts_reserve=parts_reserve,
        evidence_tax=evidence_tax,
        reversibility=reversibility,
    )


__all__ = [
    "Adaptation",
    "ControlEfficiency",
    "EcologyEstimate",
    "KnownStores",
    "LivingInstrumentExpedition",
    "LivingInstrumentExpeditionV21",
    "LivingOutcome",
    "LivingStatus",
    "MissionQuotas",
    "Orientation",
    "PhenomenonEntry",
    "RepairTarget",
    "RevealedEcology",
    "RevealedLivingState",
    "SalvageTarget",
    "ShiftPlan",
    "ShiftReceipt",
    "SurveyMode",
    "SurveyReading",
    "SystemCue",
    "control_efficiency",
]
