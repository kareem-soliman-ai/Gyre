"""Hierarchical heterogeneity for the Living Instrument Expedition v2.2.

The v2.1 world varies between named variables and seeds.  This version adds a
second, persistent level inside each public variant:

``family tendency + variant tendency + unit deviation + context interaction``.

Variant membership is therefore useful but incomplete.  Three of four units
follow each variant's majority weather response and one is a stable exception.
The same structure applies to individuals within each ecological trace family.
The hierarchy uses an independent random stream so importing it does not alter
the frozen v2.1 seed trajectories.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace
from enum import Enum

from gyre.challenge.living_expedition import (
    Adaptation,
    KnownStores,
    LivingInstrumentExpeditionV21,
    LivingOutcome,
    LivingStatus,
    Orientation,
    ShiftPlan,
    SurveyMode,
    SurveyReading,
    SystemCue,
)


class OperationalFamily(str, Enum):
    FOOD = "food"
    CARGO = "cargo"
    CREW = "crew"
    POWER = "power"
    DRIVE = "drive"


class ResponseDirection(str, Enum):
    DECREASES = "decreases"
    STABLE = "stable"
    INCREASES = "increases"


@dataclass(frozen=True)
class PublicVariant:
    """Player-facing group label and its selectable stable units."""

    family: OperationalFamily
    variant_id: str
    cue: str
    unit_ids: tuple[str, ...]


@dataclass(frozen=True)
class PublicOrganismFamily:
    trace_id: str
    individual_ids: tuple[str, ...]


@dataclass(frozen=True)
class HierarchicalStatus:
    """v2.1 status plus public nested catalogues."""

    base: LivingStatus
    variants: dict[OperationalFamily, tuple[PublicVariant, ...]]
    organisms: tuple[PublicOrganismFamily, ...]

    @property
    def shift(self) -> int:
        return self.base.shift

    @property
    def shifts_remaining(self) -> int:
        return self.base.shifts_remaining

    @property
    def incoming_weather(self) -> str:
        return self.base.incoming_weather

    @property
    def stores(self) -> KnownStores:
        return self.base.stores

    @property
    def quotas(self):
        return self.base.quotas

    @property
    def cues(self):
        return self.base.cues

    @property
    def phenomena(self):
        return self.base.phenomena

    @property
    def capacity_losses(self):
        return self.base.capacity_losses


@dataclass(frozen=True)
class HierarchicalShiftPlan:
    """One v2.1 allocation with optional stable-unit selections."""

    allocation: ShiftPlan = field(default_factory=ShiftPlan)
    food_unit: str | None = None
    cargo_unit: str | None = None
    crew_unit: str | None = None
    power_unit: str | None = None
    drive_unit: str | None = None
    organism_subject: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.allocation, ShiftPlan):
            raise TypeError("allocation must be a ShiftPlan")


@dataclass(frozen=True)
class VariantEstimate:
    weather_response: ResponseDirection
    exception_fraction: float
    confidence: float


@dataclass(frozen=True)
class RevealedUnit:
    family: OperationalFamily
    variant_id: str
    unit_id: str
    base_multiplier: float
    weather_slope: float
    load_slope: float
    persistent_offset: float
    weather_response: ResponseDirection
    exception_to_variant_rule: bool

    def effect_at(self, *, weather: float, load: float) -> float:
        """Return this unit's latent multiplier for a terminal audit."""

        if not math.isfinite(weather) or not 0.0 <= weather <= 1.0:
            raise ValueError("weather must be in [0, 1]")
        if not math.isfinite(load) or not 0.0 <= load <= 1.0:
            raise ValueError("load must be in [0, 1]")
        return max(
            0.45,
            min(
                1.55,
                self.base_multiplier
                + self.persistent_offset
                + self.weather_slope * (weather - 0.5)
                + self.load_slope * (load - 0.5),
            ),
        )


@dataclass(frozen=True)
class RevealedVariant:
    family: OperationalFamily
    variant_id: str
    cue: str
    majority_weather_response: ResponseDirection
    units: tuple[RevealedUnit, ...]


@dataclass(frozen=True)
class RevealedOrganism:
    unit_id: str
    orientation: Orientation
    adaptation: Adaptation
    response_scale: float
    detectability_offset: float
    final_reactivity: float
    exception_to_family_rule: bool


@dataclass(frozen=True)
class RevealedOrganismFamily:
    trace_id: str
    majority_orientation: Orientation
    majority_adaptation: Adaptation
    individuals: tuple[RevealedOrganism, ...]


@dataclass(frozen=True)
class HierarchicalShiftReceipt:
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
    selected_units: dict[OperationalFamily, str]
    unit_effects: dict[OperationalFamily, float]
    organism_subject: str | None


@dataclass(frozen=True)
class HierarchicalOutcome:
    base: LivingOutcome
    majority_rule_score: float
    exception_calibration_score: float
    hierarchical_recovery_score: float
    revealed_variants: dict[OperationalFamily, tuple[RevealedVariant, ...]]
    revealed_organisms: dict[str, RevealedOrganismFamily]


@dataclass(frozen=True)
class _VariantTemplate:
    base_multiplier: float
    weather_slope: float
    load_slope: float
    cue: str


@dataclass(frozen=True)
class _UnitProfile:
    family: OperationalFamily
    variant_id: str
    unit_id: str
    base_multiplier: float
    weather_slope: float
    load_slope: float
    persistent_offset: float
    exception: bool

    def effect_at(self, weather: float, load: float) -> float:
        return max(
            0.45,
            min(
                1.55,
                self.base_multiplier
                + self.persistent_offset
                + self.weather_slope * (weather - 0.5)
                + self.load_slope * (load - 0.5),
            ),
        )


@dataclass
class _OrganismProfile:
    trace_id: str
    unit_id: str
    orientation: Orientation
    adaptation: Adaptation
    response_scale: float
    detectability_offset: float
    exception: bool
    reactivity: float = 1.0


_VARIANT_CODES = ("17", "42", "88")
_UNIT_CODES = ("a", "b", "c", "d")
_PREFIXES = {
    OperationalFamily.FOOD: "bed",
    OperationalFamily.CARGO: "crate",
    OperationalFamily.CREW: "watch",
    OperationalFamily.POWER: "source",
    OperationalFamily.DRIVE: "motor",
}

_TEMPLATES = {
    OperationalFamily.FOOD: (
        _VariantTemplate(
            1.16,
            -0.34,
            0.08,
            "Broad translucent leaves rise quickly but curl before charged rain.",
        ),
        _VariantTemplate(
            0.91,
            0.27,
            -0.05,
            "Dense low growth keeps its colour when the pressure falls.",
        ),
        _VariantTemplate(
            1.02,
            -0.12,
            0.16,
            "Jointed stalks respond strongly when tended in concentrated bursts.",
        ),
    ),
    OperationalFamily.CARGO: (
        _VariantTemplate(
            1.15,
            -0.23,
            0.18,
            "Wide containers nest efficiently, though their seams sing in crosswind.",
        ),
        _VariantTemplate(
            0.90,
            0.31,
            -0.07,
            "Compact dark cases remain quiet as static builds around the press.",
        ),
        _VariantTemplate(
            1.03,
            -0.14,
            0.09,
            "Ribbed carriers settle best when the line is kept at an even rhythm.",
        ),
    ),
    OperationalFamily.CREW: (
        _VariantTemplate(
            1.13,
            -0.29,
            0.13,
            "This watch works rapidly in clear air and becomes terse before squalls.",
        ),
        _VariantTemplate(
            0.92,
            0.25,
            -0.06,
            "This watch moves slowly at first but coordinates closely under pressure.",
        ),
        _VariantTemplate(
            1.01,
            -0.11,
            0.18,
            "This watch settles into a strong cadence when given one concentrated task.",
        ),
    ),
    OperationalFamily.POWER: (
        _VariantTemplate(
            1.18,
            -0.38,
            0.04,
            "The pale vanes turn freely in clear intervals and stutter in charged air.",
        ),
        _VariantTemplate(
            0.89,
            0.34,
            -0.08,
            "The grounded coils wake as pressure falls but idle in still weather.",
        ),
        _VariantTemplate(
            1.02,
            -0.10,
            0.11,
            "The sealed cells keep a restrained, regular pulse under sustained draw.",
        ),
    ),
    OperationalFamily.DRIVE: (
        _VariantTemplate(
            1.14,
            -0.30,
            0.16,
            "The light motor spins eagerly, with a tremor that grows before storms.",
        ),
        _VariantTemplate(
            0.91,
            0.24,
            -0.05,
            "The heavy motor starts reluctantly and holds its line in violent bands.",
        ),
        _VariantTemplate(
            1.04,
            -0.13,
            0.12,
            "The segmented motor smooths out only after the press reaches a steady load.",
        ),
    ),
}


def _direction(slope: float) -> ResponseDirection:
    if slope > 0.075:
        return ResponseDirection.INCREASES
    if slope < -0.075:
        return ResponseDirection.DECREASES
    return ResponseDirection.STABLE


def _different_orientation(orientation: Orientation) -> Orientation:
    if orientation is Orientation.AVOIDANCE:
        return Orientation.ATTRACTION
    return Orientation.AVOIDANCE


def _different_adaptation(adaptation: Adaptation) -> Adaptation:
    order = (
        Adaptation.HABITUATION,
        Adaptation.SENSITISATION,
        Adaptation.THRESHOLD,
    )
    return order[(order.index(adaptation) + 1) % len(order)]


class LivingInstrumentExpeditionV22(LivingInstrumentExpeditionV21):
    """v2.1 plus discoverable, persistent within-variant heterogeneity."""

    version = "2.2"

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
        hierarchy_rng = random.Random((seed + 1) * 7_919)
        self._unit_profiles: dict[str, _UnitProfile] = {}
        self._variant_templates: dict[str, _VariantTemplate] = {}
        self._public_variants: dict[
            OperationalFamily, tuple[PublicVariant, ...]
        ] = {}
        for family in OperationalFamily:
            templates = list(_TEMPLATES[family])
            hierarchy_rng.shuffle(templates)
            public_variants: list[PublicVariant] = []
            for code, template in zip(_VARIANT_CODES, templates):
                variant_id = f"{_PREFIXES[family]}-{code}"
                exception_index = hierarchy_rng.randrange(len(_UNIT_CODES))
                offsets = [-0.14, -0.045, 0.055, 0.135]
                hierarchy_rng.shuffle(offsets)
                unit_ids: list[str] = []
                for index, (unit_code, offset) in enumerate(
                    zip(_UNIT_CODES, offsets)
                ):
                    unit_id = f"{variant_id}/{unit_code}"
                    exception = index == exception_index
                    weather_slope = (
                        -template.weather_slope if exception else template.weather_slope
                    )
                    self._unit_profiles[unit_id] = _UnitProfile(
                        family=family,
                        variant_id=variant_id,
                        unit_id=unit_id,
                        base_multiplier=template.base_multiplier,
                        weather_slope=weather_slope,
                        load_slope=template.load_slope,
                        persistent_offset=offset,
                        exception=exception,
                    )
                    unit_ids.append(unit_id)
                self._variant_templates[variant_id] = template
                public_variants.append(
                    PublicVariant(
                        family=family,
                        variant_id=variant_id,
                        cue=template.cue,
                        unit_ids=tuple(unit_ids),
                    )
                )
            self._public_variants[family] = tuple(public_variants)

        self._organism_profiles: dict[str, _OrganismProfile] = {}
        public_organisms: list[PublicOrganismFamily] = []
        for trace_id in self.variable_ids:
            template = self._ecology[trace_id].template
            exception_index = hierarchy_rng.randrange(len(_UNIT_CODES))
            scales = [0.78, 0.94, 1.08, 1.24]
            detectability = [-0.12, -0.035, 0.045, 0.11]
            hierarchy_rng.shuffle(scales)
            hierarchy_rng.shuffle(detectability)
            individual_ids: list[str] = []
            for index, unit_code in enumerate(_UNIT_CODES):
                unit_id = f"{trace_id}/{unit_code}"
                exception = index == exception_index
                self._organism_profiles[unit_id] = _OrganismProfile(
                    trace_id=trace_id,
                    unit_id=unit_id,
                    orientation=(
                        _different_orientation(template.orientation)
                        if exception
                        else template.orientation
                    ),
                    adaptation=(
                        _different_adaptation(template.adaptation)
                        if exception
                        else template.adaptation
                    ),
                    response_scale=scales[index],
                    detectability_offset=detectability[index],
                    exception=exception,
                )
                individual_ids.append(unit_id)
            public_organisms.append(
                PublicOrganismFamily(
                    trace_id=trace_id,
                    individual_ids=tuple(individual_ids),
                )
            )
        self._public_organisms = tuple(public_organisms)
        self._variant_estimates: dict[str, VariantEstimate] = {}
        self._hierarchical_outcome: HierarchicalOutcome | None = None

    def status(self) -> HierarchicalStatus:
        return HierarchicalStatus(
            base=super().status(),
            variants=self._public_variants,
            organisms=self._public_organisms,
        )

    def submit_variant_estimate(
        self,
        variant_id: str,
        *,
        weather_response: ResponseDirection,
        exception_fraction: float,
        confidence: float,
    ) -> VariantEstimate:
        self._require_open()
        if variant_id not in self._variant_templates:
            raise KeyError(f"unknown variant: {variant_id}")
        for name, value in (
            ("exception_fraction", exception_fraction),
            ("confidence", confidence),
        ):
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        estimate = VariantEstimate(
            weather_response=ResponseDirection(weather_response),
            exception_fraction=exception_fraction,
            confidence=confidence,
        )
        self._variant_estimates[variant_id] = estimate
        return estimate

    def advance(self, plan: HierarchicalShiftPlan) -> HierarchicalShiftReceipt:
        self._require_open()
        if not isinstance(plan, HierarchicalShiftPlan):
            raise TypeError("plan must be a HierarchicalShiftPlan")
        allocation = plan.allocation
        selected = {
            OperationalFamily.FOOD: self._resolve_unit(
                OperationalFamily.FOOD, plan.food_unit
            ),
            OperationalFamily.CARGO: self._resolve_unit(
                OperationalFamily.CARGO, plan.cargo_unit
            ),
            OperationalFamily.CREW: self._resolve_unit(
                OperationalFamily.CREW, plan.crew_unit
            ),
            OperationalFamily.POWER: self._resolve_unit(
                OperationalFamily.POWER, plan.power_unit
            ),
            OperationalFamily.DRIVE: self._resolve_unit(
                OperationalFamily.DRIVE, plan.drive_unit
            ),
        }
        subject = self._resolve_organism_subject(
            allocation,
            plan.organism_subject,
        )
        weather = self._weather[self._shift]
        load = {
            OperationalFamily.FOOD: allocation.cultivation / self.power_ceiling,
            OperationalFamily.CARGO: allocation.fabrication / self.power_ceiling,
            OperationalFamily.CREW: (
                allocation.cultivation
                + allocation.fabrication
                + allocation.shelter
            )
            / self.power_ceiling,
            OperationalFamily.POWER: (
                allocation.cultivation
                + allocation.fabrication
                + allocation.shelter
                + allocation.repair_units
            )
            / self.power_ceiling,
            OperationalFamily.DRIVE: allocation.fabrication / self.power_ceiling,
        }
        effects = {
            family: self._unit_profiles[unit_id].effect_at(
                weather,
                max(0.0, min(1.0, load[family])),
            )
            for family, unit_id in selected.items()
        }

        charge_before = self._charge
        individual_response = self._individual_response(
            subject,
            allocation,
        )
        base_receipt = super().advance(allocation)

        crew_factor = effects[OperationalFamily.CREW]
        food_factor = effects[OperationalFamily.FOOD] * (
            0.90 + 0.10 * crew_factor
        )
        cargo_factor = (
            effects[OperationalFamily.CARGO]
            * effects[OperationalFamily.DRIVE]
            * (0.90 + 0.10 * crew_factor)
        )
        actual_food = base_receipt.food_delta * food_factor
        actual_cargo = base_receipt.cargo_delta * cargo_factor
        self._food_produced += actual_food - base_receipt.food_delta
        self._rations += actual_food - base_receipt.food_delta
        self._cargo_produced += actual_cargo - base_receipt.cargo_delta

        self._crew = self._clamp(self._crew + 2.0 * (crew_factor - 1.0))
        self._minimum_crew = min(self._minimum_crew, self._crew)

        desired_generation = (
            base_receipt.generated_charge * effects[OperationalFamily.POWER]
        )
        charge_after_spend = max(0.0, charge_before - base_receipt.power_spent)
        self._charge = min(60.0, charge_after_spend + desired_generation)
        actual_generation = self._charge - charge_after_spend

        survey = base_receipt.survey
        ecology_shift = base_receipt.ecology_shift
        disturbance = base_receipt.disturbance
        if subject is not None and allocation.survey_mode is not SurveyMode.NONE:
            profile = self._organism_profiles[subject]
            state = self._ecology[profile.trace_id]
            if allocation.survey_mode is SurveyMode.ACTIVE:
                assert individual_response is not None
                ecology_shift = individual_response
                state.abundance = self._clamp01(
                    state.abundance
                    + individual_response
                    - base_receipt.ecology_shift
                )
                disturbance = (
                    abs(individual_response) + 0.06 * allocation.survey_intensity
                )
                self._disturbance += disturbance - base_receipt.disturbance
                self._update_individual_reactivity(profile)
            if survey is not None:
                visible_abundance = self._clamp01(
                    state.abundance + profile.detectability_offset
                )
                survey = SurveyReading(
                    variable_id=survey.variable_id,
                    mode=survey.mode,
                    intensity=survey.intensity,
                    numeric_reading=survey.numeric_reading,
                    field_cue=(
                        f"{subject}: {self._abundance_cue(visible_abundance)}"
                    ),
                )

        stores = self._known_stores()
        return HierarchicalShiftReceipt(
            shift=base_receipt.shift,
            weather=base_receipt.weather,
            power_spent=base_receipt.power_spent,
            generated_charge=actual_generation,
            food_delta=actual_food,
            cargo_delta=actual_cargo,
            survey=survey,
            ecology_shift=ecology_shift,
            disturbance=disturbance,
            stores=stores,
            cues=self._system_cues(),
            selected_units=selected,
            unit_effects=effects,
            organism_subject=subject,
        )

    def finish(self) -> HierarchicalOutcome:
        if self._hierarchical_outcome is not None:
            return self._hierarchical_outcome
        base = super().finish()
        majority_score, exception_score = self._recovery_scores()
        self._hierarchical_outcome = HierarchicalOutcome(
            base=base,
            majority_rule_score=majority_score,
            exception_calibration_score=exception_score,
            hierarchical_recovery_score=(
                0.7 * majority_score + 0.3 * exception_score
            ),
            revealed_variants={
                family: tuple(
                    self._reveal_variant(public_variant)
                    for public_variant in self._public_variants[family]
                )
                for family in OperationalFamily
            },
            revealed_organisms={
                public.trace_id: self._reveal_organism_family(public)
                for public in self._public_organisms
            },
        )
        return self._hierarchical_outcome

    def _resolve_unit(
        self,
        family: OperationalFamily,
        unit_id: str | None,
    ) -> str:
        selected = (
            self._public_variants[family][0].unit_ids[0]
            if unit_id is None
            else unit_id
        )
        profile = self._unit_profiles.get(selected)
        if profile is None or profile.family is not family:
            raise KeyError(f"unknown {family.value} unit: {selected}")
        return selected

    def _resolve_organism_subject(
        self,
        allocation: ShiftPlan,
        requested: str | None,
    ) -> str | None:
        if allocation.survey_mode is SurveyMode.NONE:
            if requested is not None:
                raise ValueError("organism_subject requires a survey")
            return None
        if allocation.survey_focus is None:
            return requested
        if requested is None:
            candidates = tuple(
                profile.unit_id
                for profile in self._organism_profiles.values()
                if profile.trace_id == allocation.survey_focus
            )
            if not candidates:
                return None
            return candidates[self._shift % len(candidates)]
        profile = self._organism_profiles.get(requested)
        if profile is None:
            raise KeyError(f"unknown organism: {requested}")
        if profile.trace_id != allocation.survey_focus:
            raise ValueError(
                "organism_subject must belong to the survey_focus trace"
            )
        return requested

    def _individual_response(
        self,
        subject: str | None,
        allocation: ShiftPlan,
    ) -> float | None:
        if (
            subject is None
            or allocation.survey_mode is not SurveyMode.ACTIVE
        ):
            return None
        profile = self._organism_profiles[subject]
        template = self._ecology[profile.trace_id].template
        if (
            profile.adaptation is Adaptation.THRESHOLD
            and allocation.survey_intensity < template.threshold
        ):
            return 0.0
        if profile.orientation is Orientation.AVOIDANCE:
            sign = -1.0
        elif profile.orientation is Orientation.ATTRACTION:
            sign = 1.0
        else:
            sign = 1.0 if self._crop < 58.0 else -1.0
        return (
            sign
            * template.base_shift
            * allocation.survey_intensity
            * profile.response_scale
            * profile.reactivity
        )

    @staticmethod
    def _update_individual_reactivity(profile: _OrganismProfile) -> None:
        if profile.adaptation is Adaptation.HABITUATION:
            profile.reactivity = max(0.18, profile.reactivity * 0.68)
        elif profile.adaptation is Adaptation.SENSITISATION:
            profile.reactivity = min(2.1, profile.reactivity * 1.28)

    def _reveal_variant(self, public: PublicVariant) -> RevealedVariant:
        template = self._variant_templates[public.variant_id]
        return RevealedVariant(
            family=public.family,
            variant_id=public.variant_id,
            cue=public.cue,
            majority_weather_response=_direction(template.weather_slope),
            units=tuple(
                RevealedUnit(
                    family=profile.family,
                    variant_id=profile.variant_id,
                    unit_id=profile.unit_id,
                    base_multiplier=profile.base_multiplier,
                    weather_slope=profile.weather_slope,
                    load_slope=profile.load_slope,
                    persistent_offset=profile.persistent_offset,
                    weather_response=_direction(profile.weather_slope),
                    exception_to_variant_rule=profile.exception,
                )
                for unit_id in public.unit_ids
                for profile in (self._unit_profiles[unit_id],)
            ),
        )

    def _reveal_organism_family(
        self,
        public: PublicOrganismFamily,
    ) -> RevealedOrganismFamily:
        template = self._ecology[public.trace_id].template
        return RevealedOrganismFamily(
            trace_id=public.trace_id,
            majority_orientation=template.orientation,
            majority_adaptation=template.adaptation,
            individuals=tuple(
                RevealedOrganism(
                    unit_id=profile.unit_id,
                    orientation=profile.orientation,
                    adaptation=profile.adaptation,
                    response_scale=profile.response_scale,
                    detectability_offset=profile.detectability_offset,
                    final_reactivity=profile.reactivity,
                    exception_to_family_rule=profile.exception,
                )
                for unit_id in public.individual_ids
                for profile in (self._organism_profiles[unit_id],)
            ),
        )

    def _recovery_scores(self) -> tuple[float, float]:
        variant_count = len(self._variant_templates)
        if not self._variant_estimates:
            return 0.0, 0.0
        majority_points = 0.0
        exception_points = 0.0
        for variant_id, estimate in self._variant_estimates.items():
            truth = _direction(
                self._variant_templates[variant_id].weather_slope
            )
            if estimate.weather_response is truth:
                majority_points += estimate.confidence
            else:
                majority_points += 0.5 * (1.0 - estimate.confidence)
            calibration = max(
                0.0,
                1.0 - 2.0 * abs(estimate.exception_fraction - 0.25),
            )
            exception_points += (
                estimate.confidence * calibration
                + 0.5 * (1.0 - estimate.confidence)
            )
        return (
            100.0 * majority_points / variant_count,
            100.0 * exception_points / variant_count,
        )


class LivingInstrumentExpeditionV221(LivingInstrumentExpeditionV22):
    """Recovery version with stronger between-variant separation."""

    version = "2.2.1"

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
        self._unit_profiles = {
            unit_id: replace(
                profile,
                base_multiplier=(
                    1.0 + 1.5 * (profile.base_multiplier - 1.0)
                ),
            )
            for unit_id, profile in self._unit_profiles.items()
        }
        self._variant_templates = {
            variant_id: replace(
                template,
                base_multiplier=(
                    1.0 + 1.5 * (template.base_multiplier - 1.0)
                ),
            )
            for variant_id, template in self._variant_templates.items()
        }


__all__ = [
    "HierarchicalOutcome",
    "HierarchicalShiftPlan",
    "HierarchicalShiftReceipt",
    "HierarchicalStatus",
    "LivingInstrumentExpeditionV22",
    "LivingInstrumentExpeditionV221",
    "OperationalFamily",
    "PublicOrganismFamily",
    "PublicVariant",
    "ResponseDirection",
    "RevealedOrganism",
    "RevealedOrganismFamily",
    "RevealedUnit",
    "RevealedVariant",
    "VariantEstimate",
]
