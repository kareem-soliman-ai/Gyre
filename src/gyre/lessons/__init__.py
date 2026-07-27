"""Executable surprises: results that argue for measurement better than prose can.

Each lesson is a real finding from this repository's own experimental record,
packaged so you meet it the way we did — by predicting the outcome first and
being wrong. That order matters. A result you were told is a fact you file
away; a result that beat your prediction is one you can still recall next week.

    python -m gyre.lessons                # list them
    python -m gyre.lessons 1              # run one

Every lesson: states a scenario, takes your prediction, runs real code on real
labelled corpora (no fixtures, no staged numbers), shows you the answer, and
ends with the command you would run on your own loops.

Nothing here is a toy example invented for teaching. These surprised us.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence


@dataclass
class Choice:
    key: str
    text: str


@dataclass
class Lesson:
    number: int
    title: str
    one_line: str
    scenario: str
    question: str
    choices: list[Choice]
    correct: str
    run: Callable[[], str]
    """Returns the evidence block — computed live, never hard-coded."""
    lesson: str
    """What the result means. Shown only after a prediction is given."""
    next_command: str
    tags: tuple[str, ...] = field(default_factory=tuple)

    def choice_text(self, key: str) -> str:
        for c in self.choices:
            if c.key.lower() == key.lower():
                return c.text
        return "(no matching option)"


REGISTRY: dict[int, Lesson] = {}


def register(lesson: Lesson) -> Lesson:
    REGISTRY[lesson.number] = lesson
    return lesson


def all_lessons() -> list[Lesson]:
    from gyre.lessons import catalogue  # noqa: F401  (registers on import)

    return [REGISTRY[k] for k in sorted(REGISTRY)]
