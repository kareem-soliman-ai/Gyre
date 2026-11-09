"""Play the hierarchical Living Instrument Expedition (v2.2.1)."""

from __future__ import annotations

import argparse
import shlex
import sys

from gyre.challenge.hierarchical_expedition import (
    HierarchicalShiftPlan,
    LivingInstrumentExpeditionV221,
    OperationalFamily,
    ResponseDirection,
)
from gyre.challenge.living_expedition import (
    RepairTarget,
    SalvageTarget,
    ShiftPlan,
    SurveyMode,
    control_efficiency,
)


BRIEF = """
KESTREL LIVING FACTORY // HIERARCHICAL EXPEDITION

Food beds, cargo containers, crew watches, power sources, and motor units each
come in three public variants. Every variant contains four stable units. The
variant's field cue is useful, but one unit in four persistently violates its
majority weather response.

Each living trace is also a family of four individuals. Three follow the family
pattern and one responds differently. You can target an individual without
being told which one is exceptional.

Produce 22 food and 22 cargo units in fourteen shifts while keeping the crew
and storm frame above their survival floors. Exact latent profiles are revealed
only in the terminal receipt.
""".strip()

HELP = """
Commands
  status
  catalog
  use <food|cargo|crew|power|drive> <unit-id>
  shift <cultivate> <fabricate> <shelter>
  quiet <trace-id-or-individual-id> <cultivate> <fabricate> <shelter>
  active <trace-id-or-individual-id> <intensity> <cultivate> <fabricate> <shelter>
  repair <shelter|cultivation|fabricator|instrument> <units>
  salvage <storm_frame|cultivation_rig|fabricator|survey_array>
  estimate-variant <variant-id> <decreases|stable|increases>
                   <exception-fraction> <confidence>
  finish
  help
  quit
""".strip()


def _default_selections(mission: LivingInstrumentExpeditionV221) -> dict:
    return {
        family: mission.status().variants[family][0].unit_ids[0]
        for family in OperationalFamily
    }


def _plan(
    allocation: ShiftPlan,
    selections: dict[OperationalFamily, str],
    *,
    organism_subject: str | None = None,
) -> HierarchicalShiftPlan:
    return HierarchicalShiftPlan(
        allocation=allocation,
        food_unit=selections[OperationalFamily.FOOD],
        cargo_unit=selections[OperationalFamily.CARGO],
        crew_unit=selections[OperationalFamily.CREW],
        power_unit=selections[OperationalFamily.POWER],
        drive_unit=selections[OperationalFamily.DRIVE],
        organism_subject=organism_subject,
    )


def _print_catalog(mission: LivingInstrumentExpeditionV221) -> None:
    status = mission.status()
    print("\nOperational catalogue")
    for family in OperationalFamily:
        print(f"  {family.value}")
        for variant in status.variants[family]:
            print(f"    {variant.variant_id}: {variant.cue}")
            print(f"      units: {', '.join(variant.unit_ids)}")
    print("  living traces")
    for family in status.organisms:
        print(f"    {family.trace_id}: {', '.join(family.individual_ids)}")


def _print_status(
    mission: LivingInstrumentExpeditionV221,
    selections: dict[OperationalFamily, str],
) -> None:
    status = mission.status()
    stores = status.stores
    print(
        f"\nShift {status.shift}/{mission.max_shifts}; "
        f"{status.shifts_remaining} remain; next: {status.incoming_weather}"
    )
    print(
        f"  charge={stores.charge:.2f}  spares={stores.spares}  "
        f"rations={stores.stored_rations:.2f}"
    )
    print(
        f"  food={stores.food_produced:.2f}/{status.quotas.food:.0f}  "
        f"cargo={stores.cargo_produced:.2f}/{status.quotas.cargo:.0f}"
    )
    print(
        "  selected: "
        + ", ".join(
            f"{family.value}={selections[family]}"
            for family in OperationalFamily
        )
    )
    for cue in status.cues:
        print(f"  {cue.signal_id:12} {cue.description}")


def _print_receipt(receipt) -> None:
    print(
        f"shift {receipt.shift}: {receipt.weather}; "
        f"spent {receipt.power_spent:.2f}, regenerated "
        f"{receipt.generated_charge:.2f}"
    )
    print(
        f"  food +{receipt.food_delta:.2f}; "
        f"cargo +{receipt.cargo_delta:.2f}"
    )
    if receipt.survey is not None:
        reading = receipt.survey
        numeric = (
            ""
            if reading.numeric_reading is None
            else f" reading={reading.numeric_reading:.3f};"
        )
        print(f"  {numeric} {reading.field_cue}")


def _print_outcome(outcome) -> None:
    base = outcome.base
    efficiency = control_efficiency(base)
    print("\nSTORMFALL RECEIPT")
    print(f"  mission accomplished: {base.mission_accomplished}")
    print(f"  mission score:        {base.mission_score:.2f}/100")
    print(f"  control efficiency:   {efficiency.score:.2f}/100 (secondary)")
    print(
        f"  hierarchy recovery:   {outcome.hierarchical_recovery_score:.2f}/100"
    )
    print(
        f"    majority rules:     {outcome.majority_rule_score:.2f}/100\n"
        f"    exception estimate: {outcome.exception_calibration_score:.2f}/100"
    )
    for gate, passed in base.gates.items():
        print(f"  {gate:20} {passed}")
    print("\nRevealed hierarchy")
    for family, variants in outcome.revealed_variants.items():
        for variant in variants:
            exceptions = [
                unit.unit_id
                for unit in variant.units
                if unit.exception_to_variant_rule
            ]
            print(
                f"  {family.value:6} {variant.variant_id}: majority "
                f"{variant.majority_weather_response.value}; "
                f"exception={exceptions[0]}"
            )
    for trace_id, family in outcome.revealed_organisms.items():
        exception = next(
            item.unit_id
            for item in family.individuals
            if item.exception_to_family_rule
        )
        print(
            f"  {trace_id}: majority {family.majority_orientation.value}/"
            f"{family.majority_adaptation.value}; exception={exception}"
        )


def run_demo(seed: int) -> object:
    mission = LivingInstrumentExpeditionV221(seed=seed)
    print(BRIEF)
    print("\nDEMO POLICY: rotate through stable units with a fixed 3:3:2 allocation")
    while mission.status().shifts_remaining:
        index = mission.status().shift
        selections = {}
        for family in OperationalFamily:
            units = tuple(
                unit_id
                for variant in mission.status().variants[family]
                for unit_id in variant.unit_ids
            )
            selections[family] = units[index % len(units)]
        receipt = mission.advance(
            _plan(
                ShiftPlan(cultivation=3, fabrication=3, shelter=2),
                selections,
            )
        )
        _print_receipt(receipt)
    outcome = mission.finish()
    _print_outcome(outcome)
    print(
        "\nThis is a baseline, not an answer. It completed 147/200 reused public "
        "development seeds in EXP-10."
    )
    return outcome


def run_interactive(seed: int) -> object | None:
    mission = LivingInstrumentExpeditionV221(seed=seed)
    selections = _default_selections(mission)
    print(BRIEF)
    print("\n" + HELP)
    _print_status(mission, selections)
    while mission.status().shifts_remaining:
        try:
            raw = input("\nhierarchical-factory> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if not raw:
            continue
        try:
            parts = shlex.split(raw)
            command = parts[0].lower()
            if command == "help":
                print(HELP)
            elif command == "status":
                _print_status(mission, selections)
            elif command == "catalog":
                _print_catalog(mission)
            elif command == "use":
                family = OperationalFamily(parts[1])
                candidate = parts[2]
                valid = {
                    unit_id
                    for variant in mission.status().variants[family]
                    for unit_id in variant.unit_ids
                }
                if candidate not in valid:
                    raise ValueError(f"{candidate} is not a {family.value} unit")
                selections[family] = candidate
                print(f"selected {family.value} unit {candidate}")
            elif command == "shift":
                receipt = mission.advance(
                    _plan(
                        ShiftPlan(
                            cultivation=int(parts[1]),
                            fabrication=int(parts[2]),
                            shelter=int(parts[3]),
                        ),
                        selections,
                    )
                )
                _print_receipt(receipt)
            elif command in {"quiet", "active"}:
                subject = parts[1] if "/" in parts[1] else None
                trace_id = parts[1].split("/", maxsplit=1)[0]
                if command == "quiet":
                    intensity = 0.0
                    offset = 2
                    mode = SurveyMode.QUIET
                else:
                    intensity = float(parts[2])
                    offset = 3
                    mode = SurveyMode.ACTIVE
                receipt = mission.advance(
                    _plan(
                        ShiftPlan(
                            cultivation=int(parts[offset]),
                            fabrication=int(parts[offset + 1]),
                            shelter=int(parts[offset + 2]),
                            survey_mode=mode,
                            survey_focus=trace_id,
                            survey_intensity=intensity,
                        ),
                        selections,
                        organism_subject=subject,
                    )
                )
                _print_receipt(receipt)
            elif command == "repair":
                receipt = mission.advance(
                    _plan(
                        ShiftPlan(
                            repair_target=RepairTarget(parts[1]),
                            repair_units=int(parts[2]),
                        ),
                        selections,
                    )
                )
                _print_receipt(receipt)
            elif command == "salvage":
                receipt = mission.advance(
                    _plan(
                        ShiftPlan(salvage_target=SalvageTarget(parts[1])),
                        selections,
                    )
                )
                _print_receipt(receipt)
            elif command == "estimate-variant":
                estimate = mission.submit_variant_estimate(
                    parts[1],
                    weather_response=ResponseDirection(parts[2]),
                    exception_fraction=float(parts[3]),
                    confidence=float(parts[4]),
                )
                print(f"recorded estimate at confidence {estimate.confidence:.2f}")
            elif command == "finish":
                outcome = mission.finish()
                _print_outcome(outcome)
                return outcome
            elif command in {"quit", "exit"}:
                return None
            else:
                print("Unknown command. Type 'help'.")
        except (IndexError, KeyError, RuntimeError, ValueError) as exc:
            print(f"Cannot apply command: {exc}")
    outcome = mission.finish()
    _print_outcome(outcome)
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=419)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo or not sys.stdin.isatty():
        run_demo(args.seed)
    else:
        run_interactive(args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
