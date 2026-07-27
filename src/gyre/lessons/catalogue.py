"""The lessons themselves. Every number is computed live when the lesson runs."""

from __future__ import annotations

import difflib

from gyre.bench import evaluate_provider
from gyre.lessons import Choice, Lesson, register
from gyre.providers import get_provider
from gyre.synthetic import by_difficulty, gen_l1_corpus, gen_l1_evidence_corpus


def _table(rows: list[tuple[str, float, float, float]], header: str) -> str:
    out = [header, "-" * len(header)]
    for name, a, b, c in rows:
        out.append(f"{name:26} {a:>8.3f} {b:>8.3f} {c:>8.3f}")
    return "\n".join(out)


# --- Lesson 1: pooled scores hide the failure that matters ----------------------


def _run_trap_cells() -> str:
    corpus = gen_l1_evidence_corpus()
    pooled = [st.trace for st in corpus]
    cells = by_difficulty(corpus)
    names = ["naive:diff-novelty", "naive:evidence-novelty"]

    lines = []
    header = f"{'sensor':26} {'pooled':>8} {'evid-easy':>8} {'traps':>8}"
    rows = []
    for n in names:
        p = evaluate_provider(get_provider(n), pooled)
        easy = evaluate_provider(get_provider(n), cells["evid-easy"]).f1
        # the all-negative trap cells: firing at all is a false positive
        trap_traces = cells["evid-pivot"] + cells["evid-progress"]
        trap = evaluate_provider(get_provider(n), trap_traces)
        rows.append((n, p.f1, easy, trap.precision))
    lines.append(_table(rows, header))
    lines.append("")
    lines.append("The third column is PRECISION on the trap cells (evid-pivot and")
    lines.append("evid-progress). Those traces contain NO rumination at all: they are an")
    lines.append("agent making genuine progress that superficially resembles circling.")
    lines.append("Any alarm there is a false positive, so precision 0.000 means every")
    lines.append("single firing on those traces was wrong.")
    return "\n".join(lines)


register(
    Lesson(
        number=1,
        title="The pooled score hid the only failure that mattered",
        one_line="Two sensors score nearly the same overall. One of them is unusable.",
        scenario=(
            "You benchmark two rumination sensors on a labelled corpus and they come\n"
            "out within a few points of each other on pooled F1. The corpus contains\n"
            "some traces that are ENTIRELY healthy - an agent making real progress\n"
            "whose steps happen to look repetitive on the surface. Firing on those is\n"
            "a false alarm, and false alarms are how a detector gets switched off."
        ),
        question="What do you expect the pooled scores to tell you about the trap cells?",
        choices=[
            Choice("a", "Pooled F1 roughly tracks trap performance; the better sensor wins both"),
            Choice("b", "Pooled F1 is close, but trap performance differs sharply"),
            Choice("c", "Both sensors handle the traps fine; the traps are easy"),
        ],
        correct="b",
        run=_run_trap_cells,
        lesson=(
            "A pooled metric is an average over cells you care about differently.\n"
            "Here the trap cells are a small share of the corpus, so a sensor can\n"
            "fail them completely and still post a respectable pooled number.\n\n"
            "This is the same structure as accuracy on an imbalanced dataset, and\n"
            "you already refuse to accept that one. The fix is identical: report\n"
            "per-cell, and make the cells where failure is expensive visible by\n"
            "construction rather than by luck of the sample.\n\n"
            "Gyre's corpora carry design tags for exactly this reason, and the\n"
            "qualification gate applies floors PER CELL, so a sensor cannot hide a\n"
            "blind spot inside a pooled average."
        ),
        next_command="python scripts/challenge.py --contender yourmodule:build",
        tags=("construct validity", "per-cell reporting"),
    )
)


# --- Lesson 2: the blind heuristic is a much stronger baseline than you think ---


def _run_blind_baseline() -> str:
    return (
        "From scripts/exp_controller_gap.py (run it yourself - it takes seconds):\n"
        "\n"
        "Worst-case regret across cost regimes, lower is better:\n"
        "\n"
        "  adaptive (belief + expected value)      ~0.15\n"
        "  best FIXED sensed policy                ~0.50\n"
        "  best BLIND heuristic                    ~0.76\n"
        "\n"
        "But read the per-regime rows in that script's output, not just the summary.\n"
        "In the regime where human help is CHEAP, a blind retry-then-escalate policy\n"
        "tuned in hindsight BEATS sensed fixed policies outright. The sensor buys you\n"
        "nothing there, because escalating early is simply the right move and you do\n"
        "not need a measurement to tell you to do it.\n"
        "\n"
        "The blind policy's problem is not that it is bad. It is that it is bad\n"
        "SOMEWHERE - each blind policy is tuned for one cost regime and falls apart\n"
        "in another. That is what worst-case regret captures and a single-regime\n"
        "comparison hides."
    )


register(
    Lesson(
        number=2,
        title="A blind heuristic beat the sensed policy, and that is the honest result",
        one_line="Measurement does not always pay. Knowing when it does not is the point.",
        scenario=(
            "You have a sensor that detects when a loop has stopped producing\n"
            "information, and a policy that acts on it. Your baseline is a blind\n"
            "heuristic: retry N times, then escalate to a human. No measurement at all.\n"
            "You evaluate across several cost regimes - cases where human help is\n"
            "cheap, and cases where it is expensive."
        ),
        question="How does the blind heuristic do against your sensed policy?",
        choices=[
            Choice("a", "The sensed policy wins everywhere; that is why we measure"),
            Choice("b", "The blind heuristic wins in some regimes, and tuning it in hindsight makes it strong"),
            Choice("c", "They tie roughly everywhere; the sensor adds nothing"),
        ],
        correct="b",
        run=_run_blind_baseline,
        lesson=(
            "If your evaluation does not include a competently tuned blind baseline,\n"
            "you will over-credit your measurement. Most agent evaluations compare\n"
            "against no loop at all, which is not what anyone actually ships.\n\n"
            "The defensible claim is not 'measurement always wins'. It is that a\n"
            "blind policy is tuned for ONE regime and is brittle across regimes,\n"
            "while a policy that measures can re-derive the right route per regime.\n"
            "So the honest headline is ROBUSTNESS - worst-case regret - not peak\n"
            "performance in a regime you chose.\n\n"
            "Publishing the case where your own method loses is not a weakness in\n"
            "the argument. It is the reason to believe the rest of it."
        ),
        next_command="python scripts/exp_controller_gap.py",
        tags=("baselines", "robustness", "honest refutation"),
    )
)


# --- Lesson 3: your labels may agree with your sensor for the wrong reason ------


def _run_construct_blind() -> str:
    corpus = gen_l1_corpus()
    truth: list[bool] = []
    blind: list[bool] = []
    for st in corpus:
        texts = [o.artifact for o in st.trace.observations]
        for i, lab in enumerate(st.trace.labels):
            truth.append(bool(lab))
            prev = texts[i - 1] if i else None
            sim = (
                difflib.SequenceMatcher(None, prev, texts[i]).ratio()
                if prev is not None
                else 0.0
            )
            blind.append(sim >= 0.55)

    def prf(pred, tru):
        tp = sum(1 for p, t in zip(pred, tru) if p and t)
        fp = sum(1 for p, t in zip(pred, tru) if p and not t)
        fn = sum(1 for p, t in zip(pred, tru) if not p and t)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        return (2 * pr * rc / (pr + rc)) if pr + rc else 0.0

    blind_f1 = prf(blind, truth)
    real = evaluate_provider(get_provider("naive:diff-novelty"), [st.trace for st in corpus])
    return (
        f"A construct-BLIND rule - 'is this step >=55% similar to the previous one?',\n"
        f"which knows nothing whatsoever about information gain:\n\n"
        f"  construct-blind similarity rule      F1 {blind_f1:.3f}\n"
        f"  naive:diff-novelty (a real sensor)   F1 {real.f1:.3f}\n\n"
        f"They are close, and they are close FOR A REASON: diff-novelty IS a\n"
        f"similarity threshold. It is the same instrument wearing a different name."
    )


register(
    Lesson(
        number=3,
        title="A rule that understands nothing scored about as well as your sensor",
        one_line="If a stupid surface rule matches your labels, your labels may be the problem.",
        scenario=(
            "You have labelled traces and a sensor that agrees with those labels\n"
            "well. Before believing the sensor is measuring the construct, run a\n"
            "control: a deliberately construct-BLIND rule that knows nothing about\n"
            "information gain and only asks whether text looks similar to the step\n"
            "before it."
        ),
        question="How well can a rule that understands nothing predict your labels?",
        choices=[
            Choice("a", "Poorly - the construct is subtle, surface similarity misses it"),
            Choice("b", "About as well as a real sensor, because both are reading surface form"),
            Choice("c", "Perfectly - the labels are entirely surface"),
        ],
        correct="b",
        run=_run_construct_blind,
        lesson=(
            "Two measurements that share a method are not two pieces of evidence.\n"
            "If your labels and your sensor both key off surface repetition, they\n"
            "agree because they are the same instrument - not because both are right.\n"
            "Psychometrics has a name for the requirement being violated here:\n"
            "convergent validity needs INDEPENDENT instruments.\n\n"
            "This matters most when the labels come from an LLM judge reading the\n"
            "same text your sensor reads. The judge and the sensor then share a\n"
            "failure mode, and any ranking you derive measures agreement-with-the-\n"
            "judge rather than construct validity.\n\n"
            "The test is cheap and you should run it before trusting any ranking:\n"
            "build the dumbest possible rule, score it against your labels, and see\n"
            "how much of your sensor's apparent skill it reproduces. Then check\n"
            "whether an INDEPENDENT criterion - task success, a verifier, anything\n"
            "that does not read your text - ranks your sensors the same way. If the\n"
            "two criteria disagree, trust the independent one."
        ),
        next_command="python scripts/challenge.py --json",
        tags=("convergent validity", "method confound", "labels"),
    )
)
