"""Qualify discoverability and control value in the observer-effect world."""

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from gyre.challenge.observer_effects import (
    InterferenceMechanism,
    ObserverEffectProfile,
    ProbeInstrument,
    ReactiveMeasurementWorld,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CALIBRATION_INTENSITIES = (0.25, 0.5, 1.0)
FINAL_INTENSITIES = (0.35, 0.85)
CALIBRATION_REPEATS = 60
EVALUATION_EPISODES = 400
OBSERVATION_NOISE = 0.03
CALIBRATION_SEED = 8419
EVALUATION_SEED = 17389


@dataclass(frozen=True)
class NamedProfile:
    name: str
    tier: str
    profile: ObserverEffectProfile


PROFILES = (
    NamedProfile("null", "null", ObserverEffectProfile()),
    NamedProfile(
        "low_linear",
        "low",
        ObserverEffectProfile(0.04, 0.02, 0.02, InterferenceMechanism.LINEAR),
    ),
    NamedProfile(
        "medium_linear",
        "medium",
        ObserverEffectProfile(0.15, 0.08, 0.06, InterferenceMechanism.LINEAR),
    ),
    NamedProfile(
        "high_linear",
        "high",
        ObserverEffectProfile(0.35, 0.18, 0.14, InterferenceMechanism.LINEAR),
    ),
    NamedProfile(
        "medium_saturating",
        "medium",
        ObserverEffectProfile(
            0.15,
            0.08,
            0.06,
            InterferenceMechanism.SATURATING,
        ),
    ),
    NamedProfile(
        "medium_threshold",
        "medium",
        ObserverEffectProfile(
            0.15,
            0.08,
            0.06,
            InterferenceMechanism.THRESHOLD,
        ),
    ),
    NamedProfile(
        "measurand_dominant",
        "dominant",
        ObserverEffectProfile(
            0.28,
            0.03,
            0.03,
            InterferenceMechanism.THRESHOLD,
        ),
    ),
    NamedProfile(
        "mechanism_dominant",
        "dominant",
        ObserverEffectProfile(
            0.03,
            0.20,
            0.03,
            InterferenceMechanism.SATURATING,
        ),
    ),
    NamedProfile(
        "measurement_dominant",
        "dominant",
        ObserverEffectProfile(
            0.03,
            0.03,
            0.22,
            InterferenceMechanism.LINEAR,
        ),
    ),
    NamedProfile(
        "signed_mixed",
        "high",
        ObserverEffectProfile(
            -0.20,
            0.14,
            -0.12,
            InterferenceMechanism.SATURATING,
        ),
    ),
)


def _calibration_episode(
    profile: ObserverEffectProfile,
    *,
    intensity: float,
    seed: int,
) -> tuple[float, float, float]:
    """Estimate three effects from observable interactions, never oracle state."""

    rng = random.Random(seed)
    world = ReactiveMeasurementWorld(
        initial_state=rng.uniform(-1.5, 1.5),
        profile=profile,
        observation_noise=OBSERVATION_NOISE,
    )
    active_before = world.probe(
        ProbeInstrument.ACTIVE,
        intensity=intensity,
        seed=rng.randrange(2**31),
    ).reading
    reference_after = world.probe(
        ProbeInstrument.REFERENCE,
        intensity=0.0,
        seed=rng.randrange(2**31),
    ).reading
    world.act(1.0)
    reference_after_control = world.probe(
        ProbeInstrument.REFERENCE,
        intensity=0.0,
        seed=rng.randrange(2**31),
    ).reading
    active_after = world.probe(
        ProbeInstrument.ACTIVE,
        intensity=0.0,
        seed=rng.randrange(2**31),
    ).reading
    return (
        reference_after - active_before,
        reference_after_control - reference_after - 1.0,
        active_after - reference_after_control,
    )


def collect_curve(
    profile: ObserverEffectProfile,
    *,
    repeats: int = CALIBRATION_REPEATS,
    seed: int = CALIBRATION_SEED,
) -> dict[float, tuple[float, float, float]]:
    rng = random.Random(seed)
    curve = {}
    for intensity in CALIBRATION_INTENSITIES:
        samples = [
            _calibration_episode(
                profile,
                intensity=intensity,
                seed=rng.randrange(2**31),
            )
            for _ in range(repeats)
        ]
        curve[intensity] = tuple(
            sum(sample[path] for sample in samples) / len(samples)
            for path in range(3)
        )
    return curve


def _candidate_response(
    mechanism: InterferenceMechanism,
    intensity: float,
) -> float:
    return ObserverEffectProfile(mechanism=mechanism).response_at(intensity)


def fit_profile(
    curve: dict[float, tuple[float, float, float]],
) -> tuple[ObserverEffectProfile, dict[str, float]]:
    """Fit a response family and one coefficient per causal path by least squares."""

    candidates = []
    for mechanism in InterferenceMechanism:
        responses = [
            _candidate_response(mechanism, intensity)
            for intensity in CALIBRATION_INTENSITIES
        ]
        denominator = sum(response * response for response in responses)
        coefficients = []
        squared_error = 0.0
        for path in range(3):
            observations = [
                curve[intensity][path] for intensity in CALIBRATION_INTENSITIES
            ]
            coefficient = sum(
                response * observation
                for response, observation in zip(responses, observations)
            ) / denominator
            coefficients.append(coefficient)
            squared_error += sum(
                (observation - coefficient * response) ** 2
                for response, observation in zip(responses, observations)
            )
        candidates.append((squared_error, mechanism, coefficients))
    squared_error, mechanism, coefficients = min(
        candidates,
        key=lambda candidate: (candidate[0], candidate[1].value),
    )
    fitted = ObserverEffectProfile(
        measurand_shift=coefficients[0],
        mechanism_shift=coefficients[1],
        instrument_bias_shift=coefficients[2],
        mechanism=mechanism,
    )
    diagnostics = {
        candidate[1].value: candidate[0] for candidate in candidates
    }
    diagnostics["selected_sse"] = squared_error
    return fitted, diagnostics


def _control_episode(
    true_profile: ObserverEffectProfile,
    assumed_profile: ObserverEffectProfile | None,
    *,
    seed: int,
) -> float:
    rng = random.Random(seed)
    world = ReactiveMeasurementWorld(
        initial_state=rng.uniform(-2.0, 2.0),
        profile=true_profile,
        observation_noise=OBSERVATION_NOISE,
    )
    readings = []
    for intensity in FINAL_INTENSITIES:
        readings.append(
            world.probe(
                ProbeInstrument.ACTIVE,
                intensity=intensity,
                seed=rng.randrange(2**31),
            ).reading
        )

    if assumed_profile is None:
        current_state_estimate = readings[-1]
        gain_estimate = 1.0
    else:
        effects = [
            assumed_profile.effect_at(intensity)
            for intensity in FINAL_INTENSITIES
        ]
        prior_bias = sum(
            effect.instrument_bias_shift for effect in effects[:-1]
        )
        current_state_estimate = (
            readings[-1] - prior_bias + effects[-1].measurand_shift
        )
        gain_estimate = 1.0 + sum(
            effect.mechanism_shift for effect in effects
        )
        if abs(gain_estimate) < 0.05:
            gain_estimate = math.copysign(0.05, gain_estimate or 1.0)

    world.act(-current_state_estimate / gain_estimate)
    return world.latent_state**2


def evaluate_policy(
    true_profile: ObserverEffectProfile,
    assumed_profile: ObserverEffectProfile | None,
    *,
    seed: int,
) -> float:
    rng = random.Random(seed)
    errors = [
        _control_episode(
            true_profile,
            assumed_profile,
            seed=rng.randrange(2**31),
        )
        for _ in range(EVALUATION_EPISODES)
    ]
    return sum(errors) / len(errors)


def main() -> Path:
    rows = []
    for index, named in enumerate(PROFILES):
        curve = collect_curve(
            named.profile,
            seed=CALIBRATION_SEED + 1009 * index,
        )
        fitted, diagnostics = fit_profile(curve)
        evaluation_seed = EVALUATION_SEED + 2003 * index
        coefficient_errors = {
            name: abs(getattr(fitted, name) - getattr(named.profile, name))
            for name in (
                "measurand_shift",
                "mechanism_shift",
                "instrument_bias_shift",
            )
        }
        rows.append(
            {
                "profile": named.name,
                "tier": named.tier,
                "true": asdict(named.profile),
                "fitted": asdict(fitted),
                "family_correct": fitted.mechanism == named.profile.mechanism,
                "coefficient_absolute_errors": coefficient_errors,
                "calibration_curve": {
                    str(intensity): list(values)
                    for intensity, values in curve.items()
                },
                "fit_diagnostics": diagnostics,
                "terminal_mse": {
                    "passive_naive": evaluate_policy(
                        named.profile,
                        None,
                        seed=evaluation_seed,
                    ),
                    "exact_prior": evaluate_policy(
                        named.profile,
                        named.profile,
                        seed=evaluation_seed,
                    ),
                    "discovered": evaluate_policy(
                        named.profile,
                        fitted,
                        seed=evaluation_seed,
                    ),
                },
            }
        )

    non_null = [row for row in rows if row["tier"] != "null"]
    aggregate = {
        policy: sum(row["terminal_mse"][policy] for row in rows) / len(rows)
        for policy in ("passive_naive", "exact_prior", "discovered")
    }
    family_correct = sum(row["family_correct"] for row in non_null)
    coefficient_mae = sum(
        error
        for row in rows
        for error in row["coefficient_absolute_errors"].values()
    ) / (3 * len(rows))
    hard_rows = [
        row for row in rows if row["tier"] in {"medium", "high", "dominant"}
    ]
    gates = {
        "family_recovery_at_least_8_of_9": family_correct >= 8,
        "coefficient_mae_at_most_0_02": coefficient_mae <= 0.02,
        "discovered_within_1_25x_exact": (
            aggregate["discovered"] <= 1.25 * aggregate["exact_prior"]
        ),
        "discovered_beats_naive_aggregate": (
            aggregate["discovered"] < aggregate["passive_naive"]
        ),
        "discovered_beats_naive_in_every_hard_cell": all(
            row["terminal_mse"]["discovered"]
            < row["terminal_mse"]["passive_naive"]
            for row in hard_rows
        ),
    }
    result = {
        "experiment": "EXP-06",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "frozen_parameters": {
            "calibration_intensities": CALIBRATION_INTENSITIES,
            "final_intensities": FINAL_INTENSITIES,
            "calibration_repeats_per_intensity": CALIBRATION_REPEATS,
            "evaluation_episodes_per_profile": EVALUATION_EPISODES,
            "observation_noise_sd": OBSERVATION_NOISE,
            "calibration_seed": CALIBRATION_SEED,
            "evaluation_seed": EVALUATION_SEED,
        },
        "calibration_probe_count_per_profile": (
            len(CALIBRATION_INTENSITIES) * CALIBRATION_REPEATS * 4
        ),
        "family_recovery": {
            "correct": family_correct,
            "eligible": len(non_null),
        },
        "coefficient_mae": coefficient_mae,
        "aggregate_terminal_mse": aggregate,
        "gates": gates,
        "qualification_passed": all(gates.values()),
        "profiles": rows,
        "claim_boundary": (
            "Synthetic mechanics and identifiability evidence only. Profiles, "
            "seeds, and baseline were authored locally; no human-AI capability "
            "or real-world transfer claim follows."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / (
        "qualification_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".json"
    )
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {output}")
    return output


if __name__ == "__main__":
    main()
