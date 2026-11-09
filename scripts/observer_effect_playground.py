"""Small CLI demonstration of measurement changing the measured world."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from gyre.challenge.observer_effects import (
    DisclosureLevel,
    InterferenceMechanism,
    ObserverEffectProfile,
    ProbeInstrument,
    ReactiveMeasurementWorld,
    interference_prior,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mechanism",
        choices=[item.value for item in InterferenceMechanism],
        default=InterferenceMechanism.SATURATING.value,
    )
    parser.add_argument(
        "--disclosure",
        choices=[item.value for item in DisclosureLevel],
        default=DisclosureLevel.EXISTENCE_ONLY.value,
    )
    parser.add_argument("--intensity", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=419)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    profile = ObserverEffectProfile(
        measurand_shift=0.18,
        mechanism_shift=0.09,
        instrument_bias_shift=0.07,
        mechanism=InterferenceMechanism(args.mechanism),
    )
    prior = interference_prior(profile, DisclosureLevel(args.disclosure))
    world = ReactiveMeasurementWorld(
        initial_state=1.0,
        profile=profile,
        observation_noise=0.02,
    )
    before = world.oracle_state()
    first = world.probe(
        ProbeInstrument.ACTIVE,
        intensity=args.intensity,
        seed=args.seed,
    )
    reference = world.probe(
        ProbeInstrument.REFERENCE,
        intensity=0.0,
        seed=args.seed + 1,
    )
    second = world.probe(
        ProbeInstrument.ACTIVE,
        intensity=args.intensity,
        seed=args.seed + 2,
    )
    after = world.oracle_state()
    print(
        json.dumps(
            {
                "public_prior": asdict(prior),
                "observations_available_to_controller": {
                    "active_before_effect": asdict(first),
                    "reference_after_effect": asdict(reference),
                    "later_active": asdict(second),
                },
                "oracle_teaching_view": {
                    "before": asdict(before),
                    "after": asdict(after),
                    "warning": "Evaluator/tutorial evidence, not participant input.",
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
