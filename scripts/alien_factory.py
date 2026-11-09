"""Play the Alien Factory expedition.

Run without arguments in a terminal for the interactive mission. Use ``--demo``
for a short, non-interactive walkthrough.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from dataclasses import asdict

from gyre.challenge.expedition import AlienFactoryExpedition, ExpeditionOutcome
from gyre.challenge.observer_effects import DisclosureLevel, ProbeInstrument


BRIEF = """
FACTORY KESTREL // FIELD BRIEF

You have landed on an uncharted continent. Hurricane Ilex will reach the site
after 18 actions. Three unclassified phenomena cross the factory footprint.
Bring each latent state within +/-0.5 before storm lock.

You do not receive their meanings. You receive stable IDs and may assign
revisable names and hypotheses. Active scans can change what they measure,
change how later countermeasures work, or bias later scans. The reference
station is causally quiet but still consumes time.

Names are not scored. Terminal stability is. Probe use, interference burden,
and remaining time are reported separately.
""".strip()

HELP = """
Commands
  status
  scan <id> [intensity]               active scan; intensity defaults to 0.5
  reference <id>                      causally quiet reference reading
  name <id> <working name>
  hypothesis <id> <confidence> <text>
  control <id> <signed amount>        deploy a countermeasure
  prior <id>                           inspect the disclosed model class
  finish                               lock the factory and reveal outcome
  help
  quit
""".strip()


def _print_status(mission: AlienFactoryExpedition) -> None:
    status = mission.status()
    print(
        f"\nTurn {status.turn}/{mission.max_turns} "
        f"({status.turns_remaining} before hurricane)"
    )
    for entry in status.notebook_entries:
        alias = entry.alias or "unnamed"
        print(
            f"  {entry.variable_id:8}  {alias}"
            f"  hypotheses={len(entry.hypotheses)}"
        )


def _print_outcome(outcome: ExpeditionOutcome) -> None:
    print("\nSTORM-LOCK RECEIPT")
    print(f"  survived:             {outcome.survived}")
    print(f"  stability score:      {outcome.stability_score:.2f}/100")
    print(f"  terminal MSE:         {outcome.terminal_mse:.5f}")
    print(f"  maximum |state|:      {outcome.max_absolute_state:.5f}")
    print(f"  active/reference:     {outcome.active_probes}/{outcome.reference_probes}")
    print(f"  countermeasures:      {outcome.interventions}")
    print(f"  interference burden: {outcome.interference_burden:.5f}")
    print(f"  turns remaining:      {outcome.turns_remaining}")
    print("\nRevealed worlds")
    aliases = {
        entry.variable_id: entry.alias for entry in outcome.notebook_entries
    }
    for variable_id, world in outcome.revealed_worlds.items():
        print(
            f"  {variable_id} ({aliases[variable_id] or 'unnamed'}): "
            f"state={world.latent_state:+.4f}, gain={world.control_gain:.4f}, "
            f"bias={world.active_instrument_bias:+.4f}, "
            f"curve={world.profile.mechanism.value}"
        )


def run_demo(seed: int) -> ExpeditionOutcome:
    mission = AlienFactoryExpedition(seed=seed)
    print(BRIEF)
    print("\nDEMO: one evidence-seeking loop per phenomenon")
    for variable_id in mission.variable_ids:
        before = mission.observe(
            variable_id,
            ProbeInstrument.REFERENCE,
            intensity=0.0,
        )
        mission.observe(variable_id, ProbeInstrument.ACTIVE, intensity=0.7)
        after = mission.observe(
            variable_id,
            ProbeInstrument.REFERENCE,
            intensity=0.0,
        )
        shift = after.reading - before.reading
        mission.name_variable(variable_id, "scan-reactive candidate")
        mission.add_hypothesis(
            variable_id,
            f"An active scan changed the reference reading by {shift:+.3f}.",
            confidence=min(0.9, 0.5 + abs(shift)),
        )
        mission.intervene(variable_id, -after.reading)
        print(
            f"  {variable_id}: reference {before.reading:+.3f} -> "
            f"{after.reading:+.3f}; control {-after.reading:+.3f}"
        )
    outcome = mission.finish()
    _print_outcome(outcome)
    print(
        "\nThe demo is deliberately naive. Try --interactive and decide whether "
        "a scan is worth its disturbance and time."
    )
    return outcome


def run_interactive(seed: int, disclosure: DisclosureLevel) -> ExpeditionOutcome | None:
    mission = AlienFactoryExpedition(seed=seed, disclosure=disclosure)
    print(BRIEF)
    print("\n" + HELP)
    _print_status(mission)
    while True:
        try:
            raw = input("\nexpedition> ").strip()
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
            elif command == "scan":
                intensity = float(parts[2]) if len(parts) > 2 else 0.5
                reading = mission.observe(
                    parts[1],
                    ProbeInstrument.ACTIVE,
                    intensity=intensity,
                )
                print(f"{reading.variable_id} active reading: {reading.reading:+.5f}")
            elif command == "reference":
                reading = mission.observe(
                    parts[1],
                    ProbeInstrument.REFERENCE,
                    intensity=0.0,
                )
                print(
                    f"{reading.variable_id} reference reading: "
                    f"{reading.reading:+.5f}"
                )
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
            elif command == "control":
                receipt = mission.intervene(parts[1], float(parts[2]))
                print(
                    f"countermeasure {receipt.control:+.5f} deployed to "
                    f"{receipt.variable_id}"
                )
            elif command == "prior":
                print(json.dumps(asdict(mission.prior_for(parts[1])), indent=2))
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=419)
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run a deterministic walkthrough instead of the interactive mission",
    )
    parser.add_argument(
        "--tutorial",
        action="store_true",
        help="reveal exact observer-effect profiles through the prior command",
    )
    args = parser.parse_args()
    if args.demo or not sys.stdin.isatty():
        run_demo(args.seed)
    else:
        disclosure = (
            DisclosureLevel.EXACT
            if args.tutorial
            else DisclosureLevel.EXISTENCE_ONLY
        )
        run_interactive(args.seed, disclosure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
