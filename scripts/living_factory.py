"""Play the coupled Living Instrument Expedition (Alien Factory v2.1)."""

from __future__ import annotations

import argparse
import shlex
import sys

from gyre.challenge.living_expedition import (
    Adaptation,
    LivingInstrumentExpeditionV21,
    Orientation,
    RepairTarget,
    SalvageTarget,
    ShiftPlan,
    SurveyMode,
    control_efficiency,
)


BRIEF = """
KESTREL LIVING FACTORY // STORMFALL BRIEF

Fourteen shifts remain. Establish a sheltered cultivation and fabrication site
before the storm closes the continent. Deliver 22 food units and 22 cargo units
while keeping the crew and storm frame above their survival floors.

Each shift has an eight-unit power ceiling. Charge, rations, spares, production,
and the next weather band are known. Five field sigils describe what the crew
can see without pretending those observations are calibrated variables.

Three living traces cross the site. Quiet surveys return coarse field signs.
Active surveys return a number, but can attract, repel, habituate, sensitise,
foul the array, or change their future contribution to the site. You may give
the traces working names and submit causal estimates. Those do not alter the
mission score.

Repairs consume spares. Salvage creates three spares by permanently reducing
one component to 62% capacity.
""".strip()

HELP = """
Commands
  status
  shift <cultivate> <fabricate> <shelter>
  quiet <trace-id> <cultivate> <fabricate> <shelter>
  active <trace-id> <intensity> <cultivate> <fabricate> <shelter>
  repair <shelter|cultivation|fabricator|instrument> <units>
  salvage <storm_frame|cultivation_rig|fabricator|survey_array>
  name <trace-id> <working name>
  hypothesis <trace-id> <confidence> <text>
  estimate <trace-id> <avoidance|attraction|contextual>
           <habituation|sensitisation|threshold> <confidence>
  finish
  help
  quit
""".strip()


def _print_status(mission: LivingInstrumentExpeditionV21) -> None:
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
    for cue in status.cues:
        print(f"  {cue.signal_id:12} {cue.description}")
    print("  living traces:")
    for entry in status.phenomena:
        print(
            f"    {entry.variable_id:8} "
            f"{entry.alias or 'unnamed':24} hypotheses={len(entry.hypotheses)}"
        )
    if status.capacity_losses:
        names = ", ".join(item.value for item in status.capacity_losses)
        print(f"  salvaged: {names}")


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
        if reading.numeric_reading is None:
            print(f"  {reading.variable_id}: {reading.field_cue}")
        else:
            print(
                f"  {reading.variable_id}: reading "
                f"{reading.numeric_reading:.3f}; {reading.field_cue}"
            )
    for cue in receipt.cues:
        print(f"  {cue.signal_id:12} {cue.description}")


def _print_outcome(outcome) -> None:
    efficiency = control_efficiency(outcome)
    print("\nSTORMFALL RECEIPT")
    print(f"  mission accomplished: {outcome.mission_accomplished}")
    print(f"  mission score:        {outcome.mission_score:.2f}/100")
    print(f"  control efficiency:   {efficiency.score:.2f}/100 (secondary)")
    print(f"  causal recovery:      {outcome.causal_recovery_score:.2f}/100")
    for gate, passed in outcome.gates.items():
        print(f"  {gate:20} {passed}")
    print(
        f"  food/cargo:           {outcome.food_produced:.2f}/"
        f"{outcome.cargo_produced:.2f}"
    )
    print(
        f"  active/quiet surveys: {outcome.active_surveys}/"
        f"{outcome.quiet_surveys}"
    )
    print(f"  disturbance burden:  {outcome.disturbance_burden:.3f}")
    print("\nRevealed living traces")
    for variable_id, profile in outcome.revealed_ecology.items():
        print(
            f"  {variable_id}: {profile.orientation.value}, "
            f"{profile.adaptation.value}; abundance={profile.abundance:.3f}; "
            f"cultivation={profile.cultivation_service:+.2f}, "
            f"shelter={profile.shelter_service:+.2f}, "
            f"fouling={profile.instrument_fouling:+.2f}"
        )


def run_demo(seed: int) -> object:
    mission = LivingInstrumentExpeditionV21(seed=seed)
    print(BRIEF)
    print("\nDEMO POLICY: fixed 3:3:2 allocation; no measurement or repair")
    while mission.status().shifts_remaining:
        _print_receipt(
            mission.advance(ShiftPlan(cultivation=3, fabrication=3, shelter=2))
        )
    outcome = mission.finish()
    _print_outcome(outcome)
    print(
        "\nThis policy is a baseline, not an answer. Across the public 200-seed "
        "recovery run it completed 49.5% of missions."
    )
    return outcome


def run_interactive(seed: int) -> object | None:
    mission = LivingInstrumentExpeditionV21(seed=seed)
    print(BRIEF)
    print("\n" + HELP)
    _print_status(mission)
    while mission.status().shifts_remaining:
        try:
            raw = input("\nliving-factory> ").strip()
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
                _print_status(mission)
            elif command == "shift":
                receipt = mission.advance(
                    ShiftPlan(
                        cultivation=int(parts[1]),
                        fabrication=int(parts[2]),
                        shelter=int(parts[3]),
                    )
                )
                _print_receipt(receipt)
            elif command in {"quiet", "active"}:
                if command == "quiet":
                    intensity = 0.0
                    offset = 2
                    mode = SurveyMode.QUIET
                else:
                    intensity = float(parts[2])
                    offset = 3
                    mode = SurveyMode.ACTIVE
                receipt = mission.advance(
                    ShiftPlan(
                        cultivation=int(parts[offset]),
                        fabrication=int(parts[offset + 1]),
                        shelter=int(parts[offset + 2]),
                        survey_mode=mode,
                        survey_focus=parts[1],
                        survey_intensity=intensity,
                    )
                )
                _print_receipt(receipt)
            elif command == "repair":
                receipt = mission.advance(
                    ShiftPlan(
                        repair_target=RepairTarget(parts[1]),
                        repair_units=int(parts[2]),
                    )
                )
                _print_receipt(receipt)
            elif command == "salvage":
                receipt = mission.advance(
                    ShiftPlan(salvage_target=SalvageTarget(parts[1]))
                )
                _print_receipt(receipt)
            elif command == "name":
                entry = mission.name_variable(parts[1], " ".join(parts[2:]))
                print(f"{entry.variable_id} is now '{entry.alias}'")
            elif command == "hypothesis":
                entry = mission.add_hypothesis(
                    parts[1],
                    " ".join(parts[3:]),
                    confidence=float(parts[2]),
                )
                print(
                    f"recorded hypothesis {len(entry.hypotheses)} for "
                    f"{entry.variable_id}"
                )
            elif command == "estimate":
                estimate = mission.submit_estimate(
                    parts[1],
                    orientation=Orientation(parts[2]),
                    adaptation=Adaptation(parts[3]),
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

