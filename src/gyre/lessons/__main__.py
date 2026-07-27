"""Run the lessons. Prediction is required before the answer is shown."""

from __future__ import annotations

import argparse
import sys

from gyre.lessons import Lesson, all_lessons


def _list() -> int:
    print("Gyre lessons - real results from this repo, in the order we met them.\n")
    for les in all_lessons():
        print(f"  {les.number}. {les.title}")
        print(f"     {les.one_line}")
    print("\nRun one:  python -m gyre.lessons <n>")
    print("Each takes a couple of minutes and asks you to predict first.")
    return 0


def _ask(lesson: Lesson, assume: str | None) -> str | None:
    """Get a prediction. Returning None means the lesson is not shown.

    The prediction gate is the whole mechanism: a result you were told is a
    fact you file away, a result that beat your prediction is one you remember.
    Skipping it does not save you time, it wastes the lesson."""
    print("\n" + "=" * 72)
    print(f"LESSON {lesson.number}: {lesson.title}")
    print("=" * 72)
    print("\n" + lesson.scenario)
    print("\n" + lesson.question + "\n")
    for c in lesson.choices:
        print(f"  ({c.key}) {c.text}")

    if assume:
        print(f"\n> {assume}   [--assume]")
        return assume

    if not sys.stdin.isatty():
        print(
            "\n(no interactive terminal; re-run with --assume <a|b|c> to record a\n"
            "prediction. The answer is withheld deliberately - see --help.)"
        )
        return None

    try:
        answer = input("\nYour prediction > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    valid = {c.key.lower() for c in lesson.choices}
    while answer not in valid:
        if not answer:
            return None
        answer = input(f"Pick one of {sorted(valid)} (or blank to quit) > ").strip().lower()
        if not answer:
            return None
    return answer


def _run(number: int, assume: str | None) -> int:
    lessons = {les.number: les for les in all_lessons()}
    if number not in lessons:
        print(f"No lesson {number}. Available: {sorted(lessons)}", file=sys.stderr)
        return 1
    lesson = lessons[number]

    prediction = _ask(lesson, assume)
    if prediction is None:
        return 0

    print("\n--- what actually happens ---\n")
    print(lesson.run())

    correct = prediction == lesson.correct.lower()
    print("\n" + "-" * 72)
    if correct:
        print(f"You predicted ({prediction}) and that is right.")
        print("Worth asking: would you have predicted it before reading the scenario?")
    else:
        print(f"You predicted ({prediction}): {lesson.choice_text(prediction)}")
        print(f"The answer is ({lesson.correct}): {lesson.choice_text(lesson.correct)}")
    print("-" * 72)
    print("\n" + lesson.lesson)
    print(f"\nTry it on your own loops:\n\n    {lesson.next_command}\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "The answer is withheld until you predict because that is the entire "
            "point: being wrong is what makes a measurement result stick."
        ),
    )
    ap.add_argument("number", nargs="?", type=int, help="lesson number (omit to list)")
    ap.add_argument("--assume", help="record a prediction non-interactively (a|b|c)")
    args = ap.parse_args()
    return _list() if args.number is None else _run(args.number, args.assume)


if __name__ == "__main__":
    raise SystemExit(main())
