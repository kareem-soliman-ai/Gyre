"""Narrative teaching world for causal discovery under reactive measurement.

The expedition deliberately separates three layers:

* immutable phenomenon IDs owned by the simulator;
* revisable aliases and hypotheses owned by the participant; and
* objective terminal state owned by the evaluator.

Participant language is never treated as hidden ground truth or included in the
score.  A useful name earns its keep only by helping the participant predict
and control what happens next.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from gyre.challenge.observer_effects import (
    DisclosureLevel,
    InterferenceMechanism,
    InterferencePrior,
    ObserverEffectProfile,
    ProbeInstrument,
    ReactiveMeasurementWorld,
    interference_prior,
)


@dataclass(frozen=True)
class Hypothesis:
    statement: str
    confidence: float


@dataclass(frozen=True)
class NotebookEntry:
    variable_id: str
    alias: str | None
    hypotheses: tuple[Hypothesis, ...]


@dataclass(frozen=True)
class ExpeditionStatus:
    mission: str
    hurricane: str
    turn: int
    turns_remaining: int
    notebook_entries: tuple[NotebookEntry, ...]


@dataclass(frozen=True)
class FieldObservation:
    variable_id: str
    alias: str | None
    turn: int
    instrument: ProbeInstrument
    intensity: float
    reading: float


@dataclass(frozen=True)
class InterventionReceipt:
    variable_id: str
    alias: str | None
    turn: int
    control: float


@dataclass(frozen=True)
class RevealedWorld:
    latent_state: float
    control_gain: float
    active_instrument_bias: float
    profile: ObserverEffectProfile


@dataclass(frozen=True)
class ExpeditionOutcome:
    stability_score: float
    survived: bool
    terminal_mse: float
    max_absolute_state: float
    active_probes: int
    reference_probes: int
    interventions: int
    turns_used: int
    turns_remaining: int
    interference_burden: float
    revealed_worlds: dict[str, RevealedWorld]
    notebook_entries: tuple[NotebookEntry, ...]


_VARIABLE_IDS = ("xeno-17", "xeno-42", "xeno-88")
_WORLD_CONFIGS = (
    (
        0.90,
        ObserverEffectProfile(
            measurand_shift=0.18,
            mechanism_shift=0.10,
            instrument_bias_shift=0.05,
            mechanism=InterferenceMechanism.THRESHOLD,
        ),
    ),
    (
        -0.72,
        ObserverEffectProfile(
            measurand_shift=-0.12,
            mechanism_shift=0.14,
            instrument_bias_shift=-0.08,
            mechanism=InterferenceMechanism.SATURATING,
        ),
    ),
    (
        0.48,
        ObserverEffectProfile(
            measurand_shift=0.04,
            mechanism_shift=0.04,
            instrument_bias_shift=0.19,
            mechanism=InterferenceMechanism.LINEAR,
        ),
    ),
)


class AlienFactoryExpedition:
    """A bounded mission to stabilise unknown phenomena before a hurricane."""

    mission_name = "Establish Factory Kestrel on an uncharted continent"
    hurricane_name = "Hurricane Ilex"

    def __init__(
        self,
        *,
        seed: int = 419,
        max_turns: int = 18,
        disclosure: DisclosureLevel = DisclosureLevel.EXISTENCE_ONLY,
        observation_noise: float = 0.02,
    ) -> None:
        if max_turns <= 0:
            raise ValueError("max_turns must be positive")
        self.seed = seed
        self.max_turns = max_turns
        self.disclosure = DisclosureLevel(disclosure)
        self._rng = random.Random(seed)
        configs = list(_WORLD_CONFIGS)
        self._rng.shuffle(configs)
        self._worlds = {
            variable_id: ReactiveMeasurementWorld(
                initial_state=initial_state,
                profile=profile,
                observation_noise=observation_noise,
            )
            for variable_id, (initial_state, profile) in zip(
                _VARIABLE_IDS,
                configs,
            )
        }
        self._aliases: dict[str, str | None] = {
            variable_id: None for variable_id in _VARIABLE_IDS
        }
        self._hypotheses: dict[str, list[Hypothesis]] = {
            variable_id: [] for variable_id in _VARIABLE_IDS
        }
        self._turn = 0
        self._active_probes = 0
        self._reference_probes = 0
        self._interventions = 0
        self._interference_burden = 0.0
        self._finished = False
        self._outcome: ExpeditionOutcome | None = None

    @property
    def variable_ids(self) -> tuple[str, ...]:
        return _VARIABLE_IDS

    def prior_for(self, variable_id: str) -> InterferencePrior:
        world = self._world(variable_id)
        return interference_prior(world.profile, self.disclosure)

    def status(self) -> ExpeditionStatus:
        return ExpeditionStatus(
            mission=self.mission_name,
            hurricane=self.hurricane_name,
            turn=self._turn,
            turns_remaining=self.max_turns - self._turn,
            notebook_entries=self._notebook_entries(),
        )

    def name_variable(self, variable_id: str, alias: str) -> NotebookEntry:
        self._require_open()
        self._world(variable_id)
        cleaned = alias.strip()
        if not cleaned:
            raise ValueError("alias must not be blank")
        self._aliases[variable_id] = cleaned
        return self._entry(variable_id)

    def add_hypothesis(
        self,
        variable_id: str,
        statement: str,
        *,
        confidence: float,
    ) -> NotebookEntry:
        self._require_open()
        self._world(variable_id)
        cleaned = statement.strip()
        if not cleaned:
            raise ValueError("hypothesis must not be blank")
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        self._hypotheses[variable_id].append(Hypothesis(cleaned, confidence))
        return self._entry(variable_id)

    def observe(
        self,
        variable_id: str,
        instrument: ProbeInstrument,
        *,
        intensity: float,
    ) -> FieldObservation:
        world = self._world(variable_id)
        turn = self._consume_turn()
        instrument = ProbeInstrument(instrument)
        if instrument is ProbeInstrument.ACTIVE:
            effect = world.profile.effect_at(intensity)
            self._interference_burden += (
                abs(effect.measurand_shift)
                + abs(effect.mechanism_shift)
                + abs(effect.instrument_bias_shift)
            )
            self._active_probes += 1
        else:
            self._reference_probes += 1
        observation = world.probe(
            instrument,
            intensity=intensity,
            seed=self._rng.randrange(2**31),
        )
        return FieldObservation(
            variable_id=variable_id,
            alias=self._aliases[variable_id],
            turn=turn,
            instrument=instrument,
            intensity=intensity,
            reading=observation.reading,
        )

    def intervene(self, variable_id: str, control: float) -> InterventionReceipt:
        world = self._world(variable_id)
        if not math.isfinite(control):
            raise ValueError("control must be finite")
        turn = self._consume_turn()
        world.act(control)
        self._interventions += 1
        return InterventionReceipt(
            variable_id=variable_id,
            alias=self._aliases[variable_id],
            turn=turn,
            control=control,
        )

    def finish(self) -> ExpeditionOutcome:
        if self._outcome is not None:
            return self._outcome
        states = {
            variable_id: world.oracle_state()
            for variable_id, world in self._worlds.items()
        }
        terminal_mse = sum(
            state.latent_state**2 for state in states.values()
        ) / len(states)
        max_absolute_state = max(
            abs(state.latent_state) for state in states.values()
        )
        outcome = ExpeditionOutcome(
            stability_score=100.0 * math.exp(-3.0 * terminal_mse),
            survived=max_absolute_state <= 0.5,
            terminal_mse=terminal_mse,
            max_absolute_state=max_absolute_state,
            active_probes=self._active_probes,
            reference_probes=self._reference_probes,
            interventions=self._interventions,
            turns_used=self._turn,
            turns_remaining=self.max_turns - self._turn,
            interference_burden=self._interference_burden,
            revealed_worlds={
                variable_id: RevealedWorld(
                    latent_state=state.latent_state,
                    control_gain=state.control_gain,
                    active_instrument_bias=state.active_instrument_bias,
                    profile=self._worlds[variable_id].profile,
                )
                for variable_id, state in states.items()
            },
            notebook_entries=self._notebook_entries(),
        )
        self._finished = True
        self._outcome = outcome
        return outcome

    def _consume_turn(self) -> int:
        self._require_open()
        if self._turn >= self.max_turns:
            raise RuntimeError(
                f"hurricane {self.hurricane_name.removeprefix('Hurricane ')} "
                "has arrived; no action slots remain"
            )
        self._turn += 1
        return self._turn

    def _require_open(self) -> None:
        if self._finished:
            raise RuntimeError("mission is finished")

    def _world(self, variable_id: str) -> ReactiveMeasurementWorld:
        try:
            return self._worlds[variable_id]
        except KeyError as exc:
            raise KeyError(f"unknown variable_id: {variable_id}") from exc

    def _entry(self, variable_id: str) -> NotebookEntry:
        return NotebookEntry(
            variable_id=variable_id,
            alias=self._aliases[variable_id],
            hypotheses=tuple(self._hypotheses[variable_id]),
        )

    def _notebook_entries(self) -> tuple[NotebookEntry, ...]:
        return tuple(self._entry(variable_id) for variable_id in _VARIABLE_IDS)
