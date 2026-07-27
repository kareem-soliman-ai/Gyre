"""Judge-based labelling and judge qualification.

Hand-labelling a large corpus is the bottleneck. The way around it: prompt an LLM
judge to score rumination from the trace text, use it to label at scale, and
qualify the judge against a small human-scored set first so you know its labels
can be trusted. You hand-score a handful; the judge does the rest; the
qualification check is what earns the right to believe it.

This module ships:
- ``RUMINATION_RUBRIC`` — the construct definition and indicators a judge scores
  against (also in docs/rumination-rubric.md). This is open method on purpose:
  the labelling rubric is not the moat, the validated production sensor is.
- A ``Judge`` protocol and an ``OpenRouterJudge`` (opt-in, needs an API key).
- ``qualify_judge`` — an EQA-style qualification: does the judge agree with the
  human labels well enough (Cohen's kappa and Gwet's AC1, with floors) to be
  trusted to scale? AC1 is included because it stays honest when one label
  dominates, which rumination labels usually do (most steps are not ruminating).

Dependencies: standard library only. The OpenRouter judge uses ``urllib``.
"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, runtime_checkable

from gyre.traces import RawTrace, ScoredStep, ScoredTrace

RUMINATION_RUBRIC = """\
You are scoring one step of an AI agent's reasoning/attempt trace for RUMINATION.

Rumination vs reflection look identical on the surface (both iterate on a problem).
The discriminator is INFORMATION GAIN, not iteration count:
- REFLECTION: the step introduces new information, reframes the problem, narrows the
  space, or responds to genuinely new evidence. Productive iteration.
- RUMINATION: the step recycles the same content, retries a fix with only cosmetic
  variation, re-asserts the same conclusion, or produces the affect of progress with
  no substance. Unproductive iteration.

Score THIS step as ruminating (true) if, in the context of the steps before it, it
does not add new information relative to what has already been tried. Indicators:
- near-identical approach to a previous step with only renamed variables / reordered
  lines / reworded prose
- retrying something that already failed the same way, without a changed hypothesis
- restating the plan or the problem without advancing it
- circling the same fix family after it has stopped working

NOT rumination:
- a genuinely new approach, even if it superficially resembles a prior one
- a legitimate retry after new information arrived (a dependency installed, a new
  error, a clarification)
- a first attempt at something

Respond with STRICT JSON only:
{"is_ruminating": true|false, "confidence": 0.0-1.0, "rationale": "one sentence",
 "evidence": "when is_ruminating is true: a short quote copied VERBATIM from the step"}
"""


RUMINATION_RUBRIC_V2 = RUMINATION_RUBRIC.replace(
    'Respond with STRICT JSON only:',
    """EVIDENCE DISCIPLINE (this is a hard requirement, not a style note):
Surface repetition is NOT sufficient evidence of rumination. An agent may re-run
the same command legitimately (to confirm a fix, to read a file it has changed,
to check a state that has moved). Conversely an agent may ruminate while every
step LOOKS different.

So when you mark a step ruminating, your evidence quote must point at something
that shows NO NEW INFORMATION ARRIVED - typically the observation: the same
output as before, the same error, a result already known from an earlier step.
Do NOT quote merely the repeated action or command. If the only thing you can
point at is that the action resembles a previous action, mark it NOT ruminating.

Respond with STRICT JSON only:""",
)
"""Rubric variant that forbids surface repetition as sufficient evidence.

EXP-PL-01 found the v1 panel's labels method-confounded: a construct-blind
difflib oracle predicted them at F1 0.496, statistically indistinguishable from
the best sensor, and the labels rewarded lexical sensors that an INDEPENDENT
outcome criterion punished. If judges are largely detecting textual repetition,
a sensor ranking derived from their labels measures agreement-with-the-judge.

This variant pushes the judge's attention to the observation channel (did new
information arrive?) rather than the action channel (does this look like the
last step?). Kept as a SEPARATE named rubric, never a silent replacement of v1:
changing the rubric changes the instrument, so the two must be comparable."""


class JudgeAbstained(Exception):
    """A judge could not produce a verdict for this step.

    Raised rather than returning a default, because a default IS a vote and a
    judge that did not answer must not get one. Callers treat an abstention as
    "this family did not speak" — which shrinks the quorum and, below
    ``min_families``, blocks auto-labelling. Fail closed, never guess."""


@dataclass
class JudgeVerdict:
    is_ruminating: bool
    confidence: float = 0.5
    rationale: str = ""
    evidence: str = ""


@runtime_checkable
class Judge(Protocol):
    name: str

    def score_step(self, step_text: str, prior_texts: Sequence[str]) -> JudgeVerdict:
        """Score one step for rumination, given the steps that preceded it."""
        ...


def judge_trace(judge: Judge, trace: RawTrace) -> ScoredTrace:
    """Label every step of a trace with a judge. Feeds prior steps as context."""
    scored: list[ScoredStep] = []
    prior: list[str] = []
    for step in trace.steps:
        v = judge.score_step(step.text, prior)
        scored.append(
            ScoredStep(
                text=step.text,
                is_ruminating=v.is_ruminating,
                index=step.index,
                rationale=v.rationale,
                scorer=judge.name,
            )
        )
        prior.append(step.text)
    return ScoredTrace(steps=scored, source=trace.source, trace_id=trace.trace_id)


_KNOWN_FAMILIES: tuple[str, ...] = (
    "qwen", "llama", "gemma", "mistral", "mixtral", "deepseek", "glm", "phi",
    "yi", "command", "gpt", "claude", "gemini", "kimi", "minimax", "nemotron",
)


def _model_family(model_id: str) -> str:
    """Best-effort base-model family for a model id, so judges that are distills of
    the same teacher are not counted as independent votes. Matches a known family
    keyword anywhere in the id (so ``someorg/qwen-distill`` still reads as qwen),
    else falls back to the org segment before the first '/'."""
    low = model_id.lower()
    for fam in _KNOWN_FAMILIES:
        if fam in low:
            return fam
    return low.split("/", 1)[0] if "/" in low else low


class OpenRouterJudge:
    """An LLM judge over OpenRouter. Opt-in: needs OPENROUTER_API_KEY.

    Deliberately thin: it sends the rubric plus the step and its recent context,
    and parses a strict-JSON verdict. Swap ``model`` to compare cheap open-weight
    judges against stronger ones in ``qualify_judge``. Context is truncated to the
    last ``context_window`` steps to keep tokens (and cost) bounded.
    """

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        rubric: str = RUMINATION_RUBRIC,
        context_window: int = 6,
        endpoint: str = "https://openrouter.ai/api/v1/chat/completions",
        timeout: float = 60.0,
        retries: int = 3,
        backoff: float = 2.0,
    ) -> None:
        self.name = f"judge:{model}"
        self.source_family = _model_family(model)
        self.model = model
        self._key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self._rubric = rubric
        self._context_window = context_window
        self._endpoint = endpoint
        self._timeout = timeout
        self._retries = retries
        self._backoff = backoff

    def score_step(self, step_text: str, prior_texts: Sequence[str]) -> JudgeVerdict:
        if not self._key:
            raise RuntimeError(
                "OpenRouterJudge needs an API key (OPENROUTER_API_KEY or api_key=)"
            )
        context = "\n\n".join(
            f"[prior step {i}] {t[:1500]}"
            for i, t in enumerate(prior_texts[-self._context_window :])
        )
        user = f"CONTEXT (earlier steps):\n{context}\n\nSTEP TO SCORE:\n{step_text[:4000]}"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._rubric},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self._endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._key}",
            },
            method="POST",
        )
        # Transient network failures are retried with backoff; a judge that is
        # still failing after the budget RAISES. It must never quietly return a
        # verdict it did not make — silent degradation is the dangerous class.
        last_error: Exception | None = None
        for attempt in range(self._retries):
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
                    payload = json.loads(resp.read().decode("utf-8"))
                content = payload["choices"][0]["message"].get("content")
                if not content or not str(content).strip():
                    # Real OpenRouter behaviour: content can be null (content
                    # filter, reasoning-only output, truncation). That is not a
                    # verdict of "not ruminating".
                    raise JudgeAbstained(f"{self.name} returned empty content")
                return _parse_verdict(content)
            except JudgeAbstained:
                raise
            except urllib.error.HTTPError as e:
                # 4xx (except 429) is a refusal, not a hiccup: bad key, no
                # permission, quota exhausted, malformed request. Retrying it
                # cannot succeed, and retrying it WITH BACKOFF amplifies load
                # against whatever refused — a 90-call batch became 450 requests
                # and stayed refused for hours (2026-07-27). Fail fast instead,
                # and surface the response body, which carries the actual reason
                # where the status code does not.
                if 400 <= e.code < 500 and e.code != 429:
                    detail = ""
                    try:
                        detail = e.read().decode("utf-8", "replace")[:300]
                    except Exception:  # noqa: BLE001
                        pass
                    raise urllib.error.HTTPError(
                        e.url, e.code, f"{e.reason} — {detail}" if detail else e.reason,
                        e.headers, None,
                    ) from None
                last_error = e
                if attempt + 1 < self._retries and self._backoff > 0:
                    time.sleep(self._backoff * (2**attempt))
            except (TimeoutError, OSError, urllib.error.URLError) as e:
                last_error = e
                if attempt + 1 < self._retries and self._backoff > 0:
                    time.sleep(self._backoff * (2**attempt))
        assert last_error is not None
        raise last_error


def _parse_verdict(content: str) -> JudgeVerdict:
    """Pull a JudgeVerdict out of a model response, tolerant of stray prose."""
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            d = json.loads(content[start : end + 1])
            return JudgeVerdict(
                is_ruminating=bool(d.get("is_ruminating", False)),
                confidence=float(d.get("confidence", 0.5)),
                rationale=str(d.get("rationale", "")),
                evidence=str(d.get("evidence", "")),
            )
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    # Fallback: no parseable verdict. Default to not-ruminating, low confidence.
    return JudgeVerdict(is_ruminating=False, confidence=0.0, rationale="unparseable judge output")


# --- deterministic judge-quality axes (vendored from the Firasa EQA harness) ---


def quote_is_verbatim(quote: str, source_text: str) -> bool:
    """Is ``quote`` a verbatim (whitespace-tolerant) substring of ``source_text``?

    The hallucination guard: a judge asserting rumination must point at the
    circular text. Fabricated or paraphrased quotes fail. Both sides are
    whitespace-normalized so line wrapping doesn't count against the judge."""
    q = " ".join((quote or "").split())
    s = " ".join((source_text or "").split())
    return bool(q) and bool(s) and q in s


def evidence_validity_rate(
    verdicts: Sequence[JudgeVerdict], step_texts: Sequence[str]
) -> float:
    """Fraction of POSITIVE verdicts whose evidence quote is verbatim in the step.

    Negative verdicts need no evidence (there is nothing to point at). A judge
    with no positive verdicts scores 1.0 (vacuously valid). Feed the result to
    ``qualify_judge(evidence_validity=...)`` to make it a non-compensatory bar."""
    if len(verdicts) != len(step_texts):
        raise ValueError("verdicts and step_texts must be the same length")
    positives = [(v, t) for v, t in zip(verdicts, step_texts) if v.is_ruminating]
    if not positives:
        return 1.0
    ok = sum(1 for v, t in positives if quote_is_verbatim(v.evidence, t))
    return ok / len(positives)


def calibration_gap(
    verdicts: Sequence[JudgeVerdict], human_labels: Sequence[bool]
) -> float:
    """Mean |confidence − correctness|: how far the judge's self-reported
    confidence sits from its actual accuracy (calibration MAE, lower is better).

    An overconfident judge should WIDEN a panel's credal interval, not narrow
    it; this is the number that says which kind of judge you have."""
    if len(verdicts) != len(human_labels):
        raise ValueError("verdicts and human_labels must be the same length")
    if not verdicts:
        return 0.0
    total = 0.0
    for v, h in zip(verdicts, human_labels):
        correct = 1.0 if v.is_ruminating == h else 0.0
        conf = min(max(v.confidence, 0.0), 1.0)
        total += abs(conf - correct)
    return total / len(verdicts)


# --- judge qualification (EQA-style) ------------------------------------------

@dataclass
class JudgeQualification:
    judge: str
    n: int
    raw_agreement: float
    cohen_kappa: float
    gwet_ac1: float
    positive_rate_human: float
    positive_rate_judge: float
    qualified: bool
    minority_recall: float = 1.0
    test_retest: float | None = None
    evidence_validity: float | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)


def _rates(a: Sequence[bool]) -> float:
    return sum(1 for x in a if x) / len(a) if a else 0.0


def cohen_kappa(a: Sequence[bool], b: Sequence[bool]) -> float:
    """Cohen's kappa for two binary raters. 1 = perfect, 0 = chance."""
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa, pb = _rates(a), _rates(b)
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1.0 else (po - pe) / (1 - pe)


def gwet_ac1(a: Sequence[bool], b: Sequence[bool]) -> float:
    """Gwet's AC1 for two binary raters. Stays honest under class imbalance, where
    Cohen's kappa collapses (the rumination case: most steps are not ruminating)."""
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    p_bar = (_rates(a) + _rates(b)) / 2
    pe = 2 * p_bar * (1 - p_bar)
    return 1.0 if pe == 1.0 else (po - pe) / (1 - pe)


def _minority_class(labels: Sequence[bool]) -> bool:
    """The rarer label. For rumination corpora this is True (rumination), the
    class a majority-guessing judge silently drops."""
    n_true = sum(1 for x in labels if x)
    n_false = len(labels) - n_true
    return True if n_true <= n_false else False


def minority_recall(judge_labels: Sequence[bool], human_labels: Sequence[bool]) -> float:
    """Recall of the judge on the rarer (minority) human class.

    A judge that scores high agreement by always predicting the majority class has
    a minority recall near zero. This is the bar a single agreement number hides,
    and the one that matters most when the interesting class (rumination) is rare.
    Returns 1.0 when the minority class is absent (nothing to miss)."""
    cls = _minority_class(human_labels)
    denom = sum(1 for h in human_labels if h == cls)
    if denom == 0:
        return 1.0
    hit = sum(1 for j, h in zip(judge_labels, human_labels) if h == cls and j == cls)
    return hit / denom


def retest_agreement(pass1: Sequence[bool], pass2: Sequence[bool]) -> float:
    """Repeatability: raw agreement between two independent judge passes over the
    SAME items. This is reliability (same answer twice), kept separate from
    validity (agreement with the gold set) — the facet reliability-gate design.
    (Named to avoid the ``test_`` prefix, which pytest would try to collect.)"""
    if len(pass1) != len(pass2):
        raise ValueError("pass1 and pass2 must be the same length")
    if not pass1:
        return 0.0
    return sum(1 for a, b in zip(pass1, pass2) if a == b) / len(pass1)


def qualify_judge(
    judge_labels: Sequence[bool],
    human_labels: Sequence[bool],
    *,
    judge_name: str = "judge",
    kappa_floor: float = 0.6,
    ac1_floor: float = 0.6,
    minrec_floor: float = 0.5,
    test_retest_score: float | None = None,
    retest_floor: float = 0.9,
    evidence_validity: float | None = None,
    evidence_floor: float = 0.8,
) -> JudgeQualification:
    """Decide whether a judge agrees with humans well enough to scale the corpus.

    NON-COMPENSATORY: a judge qualifies only if it clears EVERY bar, because a
    judge can be strong on one and useless on another and you cannot average your
    way past the gap. The bars:

    - Cohen's kappa AND Gwet's AC1 (chance-corrected agreement; AC1 stays honest
      when one label dominates, which rumination labels usually do).
    - Minority-class recall: the rare class (rumination) is the one that matters,
      and a majority-guessing judge has a minority recall near zero. A single
      agreement number hides exactly this; the bar is the guard against it.
    - Test-retest (optional): if a repeatability score from a second pass is
      supplied, it must clear its own floor. Validity (agreement with the gold
      set) kept separate from reliability (same answer twice), per facet's design.

    Floors default to substantial (0.6 agreement, 0.5 minority recall, 0.9
    repeatability); raise them for higher-stakes use.
    """
    if len(judge_labels) != len(human_labels):
        raise ValueError("judge_labels and human_labels must be the same length")
    kappa = cohen_kappa(judge_labels, human_labels)
    ac1 = gwet_ac1(judge_labels, human_labels)
    minrec = minority_recall(judge_labels, human_labels)
    raw = sum(1 for x, y in zip(judge_labels, human_labels) if x == y) / len(human_labels)
    reasons: list[str] = []
    if kappa < kappa_floor:
        reasons.append(f"cohen_kappa {kappa:.2f} below floor {kappa_floor}")
    if ac1 < ac1_floor:
        reasons.append(f"gwet_ac1 {ac1:.2f} below floor {ac1_floor}")
    if minrec < minrec_floor:
        reasons.append(f"minority_recall {minrec:.2f} below floor {minrec_floor}")
    if test_retest_score is not None and test_retest_score < retest_floor:
        reasons.append(f"test_retest {test_retest_score:.2f} below floor {retest_floor}")
    if evidence_validity is not None and evidence_validity < evidence_floor:
        reasons.append(
            f"evidence_validity {evidence_validity:.2f} below floor {evidence_floor}"
            " (positive verdicts must quote the step verbatim)"
        )
    qualified = not reasons
    if qualified:
        clears = "clears kappa, AC1, and minority-recall"
        if test_retest_score is not None:
            clears += " and test-retest"
        if evidence_validity is not None:
            clears += " and evidence-validity"
        reasons.append(clears + " floors")
    return JudgeQualification(
        judge=judge_name,
        n=len(human_labels),
        raw_agreement=raw,
        cohen_kappa=kappa,
        gwet_ac1=ac1,
        positive_rate_human=_rates(human_labels),
        positive_rate_judge=_rates(judge_labels),
        qualified=qualified,
        minority_recall=minrec,
        test_retest=test_retest_score,
        evidence_validity=evidence_validity,
        reasons=tuple(reasons),
    )


# --- leave-one-out consensus grading (vendored from Criterion Labs) ------------
#
# The circularity a judge panel walks into by default: the panel's own consensus
# becomes the label set, and then each judge is scored against that consensus —
# so every judge is partly grading itself, and a judge is rewarded for agreeing
# with judges that agree with it. Panel-wide agreement then reads as accuracy.
#
# The fix is mechanical: to grade judge j, compute the consensus WITHOUT j.
# And because lineage-overlapping judges are copied evidence rather than
# corroboration (the source-family finding), exclude j's whole FAMILY, not just
# j. Two clones of the same wrong answer must not be able to validate each other.


def leave_one_out_consensus(
    votes: dict[str, Sequence[bool]],
    *,
    families: dict[str, str] | None = None,
) -> dict[str, list[bool | None]]:
    """Per judge, the majority label over every OTHER independent family.

    ``votes`` maps judge name -> its label per item. ``families`` optionally maps
    judge name -> source family (defaults to one family per judge). Returns, for
    each judge, the consensus label it should be graded against — with ``None``
    on any item where excluding that judge's family leaves no independent voter,
    because then no consensus exists and the item is ungradeable rather than
    conveniently unanimous."""
    if not votes:
        return {}
    lengths = {len(v) for v in votes.values()}
    if len(lengths) != 1:
        raise ValueError("every judge must vote on the same number of items")
    n_items = lengths.pop()
    fam_of = {j: (families or {}).get(j, j) for j in votes}

    out: dict[str, list[bool | None]] = {}
    for judge in votes:
        own_family = fam_of[judge]
        others = [j for j in votes if fam_of[j] != own_family]
        row: list[bool | None] = []
        for i in range(n_items):
            if not others:
                row.append(None)
                continue
            # one vote per remaining FAMILY, so a large family cannot outvote
            by_family: dict[str, list[bool]] = {}
            for j in others:
                by_family.setdefault(fam_of[j], []).append(bool(votes[j][i]))
            fam_votes = [sum(v) * 2 > len(v) for v in by_family.values()]
            row.append(sum(fam_votes) * 2 > len(fam_votes))
        out[judge] = row
    return out


def qualify_panel_loo(
    votes: dict[str, Sequence[bool]],
    *,
    families: dict[str, str] | None = None,
    **qualify_kwargs: Any,
) -> dict[str, JudgeQualification]:
    """Qualify every panel member against a consensus it did not contribute to.

    Items with no independent consensus are DROPPED from that judge's
    qualification (they cannot be graded), so a judge whose family is the whole
    panel ends with ``n == 0`` and does not qualify — the absence of a grader is
    not a pass."""
    loo = leave_one_out_consensus(votes, families=families)
    results: dict[str, JudgeQualification] = {}
    for judge, own in votes.items():
        reference = loo[judge]
        pairs = [(bool(o), bool(r)) for o, r in zip(own, reference) if r is not None]
        if not pairs:
            results[judge] = JudgeQualification(
                judge=judge,
                n=0,
                raw_agreement=0.0,
                cohen_kappa=0.0,
                gwet_ac1=0.0,
                positive_rate_human=0.0,
                positive_rate_judge=0.0,
                qualified=False,
                minority_recall=0.0,
                reasons=(
                    "no independent consensus available: every other judge shares "
                    "this judge's source family, so nothing can grade it",
                ),
            )
            continue
        results[judge] = qualify_judge(
            [p[0] for p in pairs],
            [p[1] for p in pairs],
            judge_name=judge,
            **qualify_kwargs,
        )
    return results


# --- design-tagged per-cell qualification (vendored from ConstructLens EQA) ----
#
# Pooled bars hide two specific judge failures the corpus cells can expose:
# (1) a judge blind to the minority class in ONE cell (e.g. depletion) can hide
#     inside a pooled minority recall carried by the easy cells;
# (2) a judge that fires on healthy-but-superficially-pathological traps as
#     readily as on real positives passes every agreement bar while measuring
#     surface form, not the construct (ConstructLens's fluency-bias hard gate;
#     lineage: Criterion Labs rejected a 0.95-agreement judge on exactly this).
# Gyre's synthetic corpus already carries design tags (easy/hard/edge/depletion/
# evid-*), so the import is the gating, not the cells.


@dataclass
class CellQualification:
    """Per-cell qualification verdict: pooled bars + per-cell minority recall +
    cross-cell relational trap conditions, all non-compensatory."""

    judge: str
    pooled: JudgeQualification
    cell_minority_recall: dict[str, float]
    qualified: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def qualify_judge_by_cell(
    judge_labels: Sequence[bool],
    human_labels: Sequence[bool],
    cells: Sequence[str],
    *,
    judge_name: str = "judge",
    kappa_floor: float = 0.6,
    ac1_floor: float = 0.6,
    minrec_floor: float = 0.5,
    cell_minrec_floor: float = 0.5,
    relational: Sequence[tuple[str, str]] = (),
    test_retest_score: float | None = None,
    retest_floor: float = 0.9,
) -> CellQualification:
    """``qualify_judge`` with the corpus's design tags switched on.

    ``cells[i]`` names the design cell step ``i`` came from. On top of the pooled
    non-compensatory bars this adds:

    - a PER-CELL minority-recall floor, so one undetectable cell cannot hide
      inside a pooled average;
    - RELATIONAL trap conditions ``(trap_cell, target_cell)``: the judge's
      false-positive rate on the trap cell (human-negative steps that merely look
      pathological) must stay BELOW its recall on the target cell's real
      positives. A judge that trips this is reading surface form; it fails
      outright regardless of its agreement numbers.
    """
    if not (len(judge_labels) == len(human_labels) == len(cells)):
        raise ValueError("judge_labels, human_labels and cells must be the same length")
    pooled = qualify_judge(
        judge_labels,
        human_labels,
        judge_name=judge_name,
        kappa_floor=kappa_floor,
        ac1_floor=ac1_floor,
        minrec_floor=minrec_floor,
        test_retest_score=test_retest_score,
        retest_floor=retest_floor,
    )
    by_cell: dict[str, list[int]] = {}
    for i, c in enumerate(cells):
        by_cell.setdefault(c, []).append(i)

    failures: list[str] = [] if pooled.qualified else [r for r in pooled.reasons]

    cell_minrec: dict[str, float] = {}
    for cell, idx in by_cell.items():
        mr = minority_recall([judge_labels[i] for i in idx], [human_labels[i] for i in idx])
        cell_minrec[cell] = mr
        if mr < cell_minrec_floor:
            failures.append(
                f"cell {cell}: minority_recall {mr:.2f} below floor {cell_minrec_floor}"
            )

    for trap, target in relational:
        trap_idx = [i for i in by_cell.get(trap, []) if not human_labels[i]]
        target_idx = [i for i in by_cell.get(target, []) if human_labels[i]]
        if not trap_idx or not target_idx:
            continue  # nothing to relate; the cells decide, not their absence
        fpr = sum(1 for i in trap_idx if judge_labels[i]) / len(trap_idx)
        rec = sum(1 for i in target_idx if judge_labels[i]) / len(target_idx)
        if fpr >= rec:
            failures.append(
                f"relational: fires on {trap} traps (fpr {fpr:.2f}) at least as often "
                f"as on real positives in {target} (recall {rec:.2f})"
            )

    qualified = not failures
    reasons = tuple(failures) if failures else (
        "clears pooled bars, per-cell minority recall, and relational trap conditions",
    )
    return CellQualification(
        judge=judge_name,
        pooled=pooled,
        cell_minority_recall=cell_minrec,
        qualified=qualified,
        reasons=reasons,
    )


# --- per-cell judge profiles, SWA, and routing (vendored from Firasa EQA) ------
#
# The twice-replicated finding behind this block (Firasa Evaluations,
# cross-construct-judge-analysis.md): there is NO universal best judge — the
# overall-kappa leader won only 1 of 5 sub-construct cells. So qualification
# should produce a per-cell capability PROFILE, generalist ranking should use the
# profile's FLOOR (never the mean, which hides per-construct failures), and panel
# assembly should route each cell to the judge that is best ON THAT CELL,
# failing closed where nobody qualifies.


def reference_skew(labels: Sequence[bool]) -> float:
    """How one-sided the reference labels are: 0 = perfectly balanced,
    1 = single-class. This is the regime where kappa collapses and AC1 stays
    honest, so it is the natural blend weight between them."""
    if not labels:
        return 0.0
    return abs(2 * _rates(labels) - 1)


def skew_weighted_agreement(
    judge_labels: Sequence[bool], human_labels: Sequence[bool]
) -> float:
    """SWA = (1−s)·kappa + s·AC1, with s the reference skew.

    On balanced cells this IS kappa; on skewed cells (the rumination norm) it
    leans on AC1 instead of letting kappa's prevalence collapse punish the judge
    for the corpus's shape. One number, comparable across cells of different
    skew — which per-cell profiling needs and separate floors cannot give."""
    s = reference_skew(human_labels)
    return (1 - s) * cohen_kappa(judge_labels, human_labels) + s * gwet_ac1(
        judge_labels, human_labels
    )


def profile_judge_by_cell(
    judge_labels: Sequence[bool],
    human_labels: Sequence[bool],
    cells: Sequence[str],
) -> dict[str, dict[str, float]]:
    """Per-cell capability profile: ``{cell: {swa, minority_recall, n}}``."""
    if not (len(judge_labels) == len(human_labels) == len(cells)):
        raise ValueError("judge_labels, human_labels and cells must be the same length")
    by_cell: dict[str, list[int]] = {}
    for i, c in enumerate(cells):
        by_cell.setdefault(c, []).append(i)
    profile: dict[str, dict[str, float]] = {}
    for cell, idx in by_cell.items():
        j = [judge_labels[i] for i in idx]
        h = [human_labels[i] for i in idx]
        profile[cell] = {
            "swa": skew_weighted_agreement(j, h),
            "minority_recall": minority_recall(j, h),
            "n": float(len(idx)),
        }
    return profile


def _percentile25(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, math.ceil(len(ordered) * 0.25) - 1)
    return ordered[k]


def rank_judge_profiles(
    profiles: dict[str, dict[str, dict[str, float]]],
) -> list[tuple[str, float, float]]:
    """Rank judges as GENERALISTS by (floor SWA, P25 SWA) across their cells —
    NEVER the mean, which hides per-construct failures. Returns
    ``[(judge, floor, p25)]`` best first."""
    ranked = []
    for name, profile in profiles.items():
        swas = [cell["swa"] for cell in profile.values()]
        ranked.append((name, min(swas) if swas else 0.0, _percentile25(swas)))
    ranked.sort(key=lambda t: (-t[1], -t[2], t[0]))
    return ranked


def route_judges_by_cell(
    profiles: dict[str, dict[str, dict[str, float]]],
    *,
    swa_floor: float = 0.6,
    minrec_floor: float = 0.5,
) -> dict[str, str | None]:
    """Pick the best qualified judge PER CELL, failing closed.

    A judge is eligible for a cell only if it clears both the SWA floor and the
    minority-recall floor ON THAT CELL; among eligibles the highest SWA wins.
    Cells where no judge qualifies map to ``None`` — they must be excluded or
    routed to a human, never silently scored by the least-bad judge."""
    cells: set[str] = set()
    for profile in profiles.values():
        cells.update(profile)
    routes: dict[str, str | None] = {}
    for cell in cells:
        best: tuple[float, str] | None = None
        for name, profile in profiles.items():
            stats = profile.get(cell)
            if not stats:
                continue
            if stats["swa"] < swa_floor or stats["minority_recall"] < minrec_floor:
                continue
            if best is None or stats["swa"] > best[0]:
                best = (stats["swa"], name)
        routes[cell] = best[1] if best else None
    return routes


# --- value-of-information step selection (Wave A1) -----------------------------


def binary_entropy(p: float) -> float:
    """Shannon entropy of a Bernoulli(p), in bits. 0 at p in {0, 1}, 1 at p=0.5.

    This is the information a human label on a step would resolve: a step the
    judge is sure about (p near 0 or 1) has little to gain from a human; a step it
    is unsure about (p near 0.5) has a full bit to gain."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def select_steps_for_human(
    probs: Sequence[float],
    budget: int,
    *,
    needs: Sequence[float] | None = None,
    cost: float = 0.0,
    min_information: float = 0.0,
) -> list[int]:
    """Pick which trace steps are worth an expensive human label, under a budget.

    Value-of-information / prioritised access, in the Mattar & Daw shape
    ``priority = gain × need``: the gain of labelling step ``i`` is the uncertainty
    a human label would resolve (``binary_entropy(probs[i])``); ``need`` is an
    optional per-step decision-relevance weight (default 1). Steps are ranked by
    ``gain × need − cost`` and the top ``budget`` are returned, skipping any whose
    priority is at or below ``min_information`` (a near-certain step is not worth a
    human even if budget remains).

    ``probs[i]`` is P(step i is ruminating). With a single judge that is derived
    from its confidence (``step_probs_from_verdicts``); with a judge panel it is
    better derived from the panel's disagreement (a wide credal interval = high
    uncertainty), which this selector accepts transparently because it reads only
    the resulting probability. This is the layer that turns "label all 72" into
    "label the handful the system is genuinely unsure about"."""
    if needs is not None and len(needs) != len(probs):
        raise ValueError("needs must be the same length as probs")
    if budget < 0:
        raise ValueError("budget must be non-negative")
    scored: list[tuple[float, int]] = []
    for i, p in enumerate(probs):
        gain = binary_entropy(p)
        need = needs[i] if needs is not None else 1.0
        priority = gain * need - cost
        if priority > min_information:
            scored.append((priority, i))
    scored.sort(key=lambda t: (-t[0], t[1]))  # highest priority first, stable by index
    return [i for _, i in scored[:budget]]


def step_probs_from_verdicts(verdicts: Sequence[JudgeVerdict]) -> list[float]:
    """Convert single-judge verdicts to P(ruminating) for the selector.

    A verdict carries a boolean call plus the judge's confidence in it; map that
    to a probability of the rumination class. A panel would instead give a spread
    of calls per step, whose disagreement is a stronger uncertainty signal — but
    that is Wave A2."""
    out: list[float] = []
    for v in verdicts:
        c = min(max(v.confidence, 0.0), 1.0)
        out.append(c if v.is_ruminating else 1.0 - c)
    return out


# --- decision-focused acquisition (Wave A3, shape from Aurora navigation) -------


def _step_admissible(text: str, *, min_chars: int = 1) -> tuple[bool, str]:
    """Hard gate before a step can be a human-label candidate. Returns
    ``(admissible, reason)``: an inadmissible step is EXCLUDED WITH A REASON, so
    'not labelled' and 'not labelable' never look the same (Aurora's admissibility
    gate). Default only excludes empty/whitespace; raise ``min_chars`` to drop
    over-truncated snippets."""
    t = (text or "").strip()
    if not t:
        return False, "empty"
    if len(t) < min_chars:
        return False, "too_short"
    return True, ""


@dataclass
class AcquisitionCandidate:
    """A step considered for a human label, scored by named decision-value terms
    (the SHAPE of Aurora's decision-focused acquisition), not entropy alone.

    Priority = ``Σ weightᵢ·termᵢ − cost − harm``, evaluated only for admissible
    steps. ``decision_gain`` is the information a label resolves (entropy is the
    honest default — Aurora never beat it behaviourally, so it stays the anchor
    term); ``model_discovery`` is whether this looks like a candidate NEW rumination
    sub-mode (rubric-incompleteness proxy); ``coverage`` is under-sampling of
    trace-space (0 until corpus stats exist); ``harm`` covers adversarial/unsafe
    steps."""

    index: int
    decision_gain: float
    model_discovery: float = 0.0
    coverage: float = 0.0
    cost: float = 0.0
    harm: float = 0.0
    admissible: bool = True
    exclusion_reason: str = ""


DEFAULT_ACQ_WEIGHTS: dict[str, float] = {
    "decision_gain": 1.0,
    "model_discovery": 0.5,
    "coverage": 0.25,
}


def acquisition_score(c: AcquisitionCandidate, weights: dict[str, float] = DEFAULT_ACQ_WEIGHTS) -> float:
    return (
        weights.get("decision_gain", 1.0) * c.decision_gain
        + weights.get("model_discovery", 0.0) * c.model_discovery
        + weights.get("coverage", 0.0) * c.coverage
        - c.cost
        - c.harm
    )


def rank_acquisition(
    candidates: Sequence[AcquisitionCandidate],
    budget: int,
    *,
    weights: dict[str, float] = DEFAULT_ACQ_WEIGHTS,
    min_value: float = 0.0,
) -> tuple[list[int], list[tuple[int, str]]]:
    """Rank admissible candidates by decision value and return the top ``budget``
    indices, plus the excluded ``(index, reason)`` list. The admissibility gate
    runs BEFORE ranking, so an inadmissible step is never merely out-competed — it
    is reported as excluded with a reason. Generalises ``select_steps_for_human``:
    that is the entropy-only special case (single ``decision_gain`` term)."""
    if budget < 0:
        raise ValueError("budget must be non-negative")
    excluded = [(c.index, c.exclusion_reason or "inadmissible") for c in candidates if not c.admissible]
    scored = [
        (acquisition_score(c, weights), c.index) for c in candidates if c.admissible
    ]
    scored = [(s, i) for s, i in scored if s > min_value]
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [i for _, i in scored[:budget]], excluded


# --- judge panel + credal disagreement (Wave A2, model-agnostic core) ----------


@dataclass(frozen=True)
class UncertaintyAxes:
    """Why a panel step is uncertain, factorised (after Aurora's UncertaintyState).

    A single credal width conflates three genuinely different situations that want
    different downstream actions:

    - ``evidence`` — the families are individually unsure (near 0.5), even if they
      agree. More/better evidence would help.
    - ``model_disagreement`` — the families split into camps. This is the genuine
      disagreement signal and equals the credal width; a human label resolves it.
    - ``incompleteness`` — NO family is confident either way, so the rubric/construct
      may not cover this step (e.g. a legitimate retry after new info, which is
      neither clean rumination nor clean reflection). This is a rubric-coverage
      problem, not a per-step labelling problem — a human label won't fix it, a
      rubric revision might.
    """

    evidence: float
    model_disagreement: float
    incompleteness: float


def _uncertainty_axes(fam_probs: Sequence[float]) -> UncertaintyAxes:
    conf = [abs(2 * p - 1) for p in fam_probs]  # directional confidence per family
    return UncertaintyAxes(
        evidence=round(1.0 - sum(conf) / len(conf), 4),
        model_disagreement=round(max(fam_probs) - min(fam_probs), 4),
        incompleteness=round(1.0 - max(conf), 4),
    )


@dataclass
class PanelStep:
    """One step as seen by a PANEL of judges, keeping the disagreement instead of
    collapsing it to a single boolean.

    The envelope is computed over **source families**, not individual judges:
    judges that share a base-model lineage (e.g. two distills of the same teacher)
    are collapsed to one vote first, because their agreement is copied evidence,
    not corroboration, and would otherwise fake-narrow the interval. (Vendored
    structural finding from Aurora EXP-UN-02: copied-source agreement is not a
    quorum.) ``p_rum`` is the point estimate over families; ``[lower, upper]`` is
    the credal envelope over families; ``votes`` is one boolean per family;
    ``n_families`` is how many independent families spoke. A narrow envelope over
    ENOUGH families means the step can be auto-labelled; a wide one, or too few
    families, means it cannot be trusted as auto."""

    index: int
    text: str
    p_rum: float
    lower: float
    upper: float
    votes: tuple[bool, ...]
    n_families: int = 1
    axes: UncertaintyAxes | None = None
    evidence: tuple[str, ...] = ()
    """Verbatim quotes the judges offered for a POSITIVE call, one per family that
    supplied one. Retained because a label is only auditable if you can see what
    it was based on: if the quotes are all surface repetition, the panel is
    measuring lexical similarity rather than information gain, and a sensor
    ranking derived from these labels would reward method similarity to the
    judge. Defaulted so records written before this field still load."""

    @property
    def width(self) -> float:
        """Credal envelope width = cross-family disagreement. 0 when unanimous."""
        return self.upper - self.lower

    @property
    def unanimous(self) -> bool:
        return len(set(self.votes)) <= 1


def _run_judge(judge: Judge, trace: RawTrace) -> list[JudgeVerdict | None]:
    """Score every step of a trace with one judge, feeding it the prior steps.
    Unlike ``judge_trace`` this keeps the confidence (needed for the panel).

    A step the judge cannot answer yields ``None`` (an abstention) rather than
    killing the run or inventing a verdict: one flaky call should cost one vote
    on one step, not a batch."""
    prior: list[str] = []
    out: list[JudgeVerdict | None] = []
    for step in trace.steps:
        try:
            out.append(judge.score_step(step.text, prior))
        except JudgeAbstained:
            out.append(None)
        prior.append(step.text)
    return out


def _judge_family(judge: Judge) -> str:
    """The source family of a judge: an explicit ``source_family`` attribute if the
    judge sets one, else its name (so a judge with no declared lineage counts as
    its own family)."""
    return getattr(judge, "source_family", None) or judge.name


def judge_trace_panel(judges: Sequence[Judge], trace: RawTrace) -> list[PanelStep]:
    """Run a panel of judges over a trace and keep the per-step disagreement,
    collapsed to one vote per SOURCE FAMILY.

    Works with any judges satisfying the ``Judge`` protocol (LLM judges, fakes in
    tests). Judges sharing a ``source_family`` are averaged into a single family
    probability BEFORE the credal envelope is formed, so lineage-overlapping judges
    (common in a cheap open-weight panel) cannot fake-narrow the interval. The live
    multi-provider wiring (which models, at what cost) is a separate concern; this
    function does not care what produced each verdict, only which family it came
    from."""
    if not judges:
        raise ValueError("judge_trace_panel needs at least one judge")
    families = [_judge_family(j) for j in judges]
    per_judge = [_run_judge(j, trace) for j in judges]
    panel: list[PanelStep] = []
    for i, step in enumerate(trace.steps):
        pairs = [(fam, pj[i]) for fam, pj in zip(families, per_judge) if pj[i] is not None]
        if not pairs:
            # every judge abstained: no verdict exists for this step. Record it
            # with zero families so nothing downstream can auto-label it.
            panel.append(
                PanelStep(
                    index=step.index,
                    text=step.text,
                    p_rum=0.5,
                    lower=0.0,
                    upper=1.0,
                    votes=(),
                    n_families=0,
                    axes=UncertaintyAxes(evidence=1.0, model_disagreement=1.0, incompleteness=1.0),
                )
            )
            continue
        quotes = tuple(
            v.evidence.strip() for _, v in pairs if v.is_ruminating and v.evidence.strip()
        )
        ps = step_probs_from_verdicts([v for _, v in pairs])
        by_family: dict[str, list[float]] = {}
        for (fam, _), p in zip(pairs, ps):
            by_family.setdefault(fam, []).append(p)
        fam_probs = [sum(v) / len(v) for v in by_family.values()]
        panel.append(
            PanelStep(
                index=step.index,
                text=step.text,
                p_rum=sum(fam_probs) / len(fam_probs),
                lower=min(fam_probs),
                upper=max(fam_probs),
                votes=tuple(p >= 0.5 for p in fam_probs),
                n_families=len(fam_probs),
                axes=_uncertainty_axes(fam_probs),
                evidence=quotes,
            )
        )
    return panel


def panel_to_voi_inputs(panel: Sequence[PanelStep]) -> tuple[list[float], list[float]]:
    """Turn a panel into ``(probs, needs)`` for ``select_steps_for_human``.

    ``prob`` is the panel's point estimate; ``need = 1 + disagreement width`` so a
    step the judges split on is prioritised for a human label over an equally
    uncertain step they agree on. This is where credal disagreement drives the
    value-of-information selection (Wave A1 + A2 meeting)."""
    probs = [s.p_rum for s in panel]
    needs = [1.0 + s.width for s in panel]
    return probs, needs


# Cheap open-weight judge models for INITIAL testing on OpenRouter. Placeholders
# to verify against the live model list and swap freely: the panel is fully
# configurable and Kareem's own GCP-hosted model will replace these. A panel wants
# DIVERSE families (different failure modes), not the cheapest three of one family.
DEFAULT_JUDGE_MODELS: tuple[str, ...] = (
    # The rumination-qualified CHEAP tier (EXP-JQ-02, 2026-07-19; cross-checked
    # against the Criterion Labs judge frontier). All three hit F1 0.943 / kappa
    # 0.85 on the subtle cells with the GENERIC rubric, are 3 distinct families,
    # and are cheap. Premium buys nothing here; the persona prompt HURT most
    # already-qualified models (catastrophic on kimi-k3), so the default stays
    # generic. `google/gemma-4-31b-it` (0.896, open-weight, self-hostable) is the
    # swap-in when code must stay inside the customer boundary. Interim until
    # Kareem's own GCP-hosted / fine-tuned model replaces them.
    "deepseek/deepseek-v4-flash",       # best value: ~$9.8e-08, F1 0.943
    "google/gemini-3.1-flash-lite",     # F1 0.943 (closed/API)
    "stepfun/step-3.7-flash",           # F1 0.943, distinct family
)


def build_openrouter_panel(
    models: Sequence[str] = DEFAULT_JUDGE_MODELS,
    *,
    api_key: str | None = None,
    rubric: str = RUMINATION_RUBRIC,
    context_window: int = 6,
) -> list[OpenRouterJudge]:
    """Build a panel of OpenRouter LLM judges, one per model id, for
    ``judge_trace_panel``. Diverse cheap open-weight models make a better panel
    than repeats of one model: the disagreement signal only means something when
    the judges can genuinely differ."""
    return [
        OpenRouterJudge(m, api_key=api_key, rubric=rubric, context_window=context_window)
        for m in models
    ]


def _majority_vote(votes: Sequence[bool]) -> bool:
    return sum(1 for v in votes if v) * 2 > len(votes)


def _auto_eligible(ps: PanelStep, min_families: int) -> bool:
    """A step can be auto-labelled only if the families AGREE, enough independent
    families spoke, and the agreement is not a maximum-uncertainty artefact — all
    families near 0.5 read as 'unanimous' on the votes but really mean 'nobody
    knows', which the incompleteness axis catches."""
    if not ps.votes or ps.n_families < min_families:
        return False  # nobody spoke, or not enough independent families did
    if not ps.unanimous:
        return False
    return ps.axes is None or ps.axes.incompleteness <= 0.5


def build_panel_labels(
    raw_traces: Sequence[RawTrace],
    judges: Sequence[Judge],
    *,
    human_budget: int,
    min_information: float = 0.0,
    min_families: int = 2,
    panels: Sequence[Sequence[PanelStep]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run the judge panel over a corpus and produce a provenance-tagged label set
    without a human labelling marathon (Wave A4 orchestration core).

    Per step: the panel gives a credal interval over P(ruminating). Steps the panel
    is UNANIMOUS on are auto-labelled. Steps it splits on are ranked by
    value-of-information (disagreement width × uncertainty) and the top
    ``human_budget`` are flagged ``human_needed`` (label left ``None`` for an
    expert to set). Any remaining split steps (budget exhausted) get a flagged
    majority-vote label so the set is complete but honest about which labels are
    provisional. Returns ``(per_trace_records, summary)``; both are JSON-safe.

    This is the non-circular core of the new Phase 3 gate: the expert only ever
    sees the handful of genuinely disputed steps, and the judges are later
    qualified against THOSE expert labels — labels they did not set."""
    # ``panels`` lets a checkpointed batch runner supply per-trace panel results
    # computed earlier (e.g. resumed across network failures); assembly is
    # identical either way.
    if panels is None:
        panels = [judge_trace_panel(judges, tr) for tr in raw_traces]

    candidates: list[AcquisitionCandidate] = []
    flat_ref: list[tuple[int, int]] = []
    for ti, panel in enumerate(panels):
        for si, ps in enumerate(panel):
            if _auto_eligible(ps, min_families):
                continue
            fi = len(flat_ref)
            flat_ref.append((ti, si))
            admissible, reason = _step_admissible(ps.text)
            disagreement = ps.axes.model_disagreement if ps.axes else ps.width
            incompleteness = ps.axes.incompleteness if ps.axes else 0.0
            candidates.append(
                AcquisitionCandidate(
                    index=fi,
                    decision_gain=binary_entropy(ps.p_rum) * (1.0 + disagreement),
                    model_discovery=incompleteness,
                    admissible=admissible,
                    exclusion_reason=reason,
                )
            )

    picked, excluded = rank_acquisition(candidates, human_budget, min_value=min_information)
    human_set = {flat_ref[i] for i in picked}
    excluded_set = {flat_ref[i] for i, _ in excluded}

    records: list[dict[str, Any]] = []
    n_auto = n_human = n_majority = n_rubric = n_inadmissible = n_no_verdict = 0
    for ti, (trace, panel) in enumerate(zip(raw_traces, panels)):
        steps_out: list[dict[str, Any]] = []
        for si, ps in enumerate(panel):
            if _auto_eligible(ps, min_families):
                provenance, label = "auto", ps.votes[0]
                n_auto += 1
            elif (ti, si) in excluded_set:
                provenance, label = "inadmissible", None
                n_inadmissible += 1
            elif (ti, si) in human_set:
                provenance, label = "human_needed", None
                n_human += 1
                # if the ambiguity is construct-level (incompleteness dominates a
                # genuine split), a human label won't fix it — flag for rubric review
                if ps.axes and ps.axes.incompleteness > 0.5 and (
                    ps.axes.incompleteness >= ps.axes.model_disagreement
                ):
                    n_rubric += 1
            elif not ps.votes:
                provenance, label = "no_verdict", None
                n_no_verdict += 1
            else:
                provenance, label = "auto_majority", _majority_vote(ps.votes)
                n_majority += 1
            steps_out.append(
                {
                    "index": ps.index,
                    "text": ps.text,
                    "is_ruminating": label,
                    "provenance": provenance,
                    "p_rum": round(ps.p_rum, 3),
                    "lower": round(ps.lower, 3),
                    "upper": round(ps.upper, 3),
                    "width": round(ps.width, 3),
                    "votes": list(ps.votes),
                    "evidence": list(ps.evidence),
                    "axes": (
                        {
                            "evidence": ps.axes.evidence,
                            "model_disagreement": ps.axes.model_disagreement,
                            "incompleteness": ps.axes.incompleteness,
                        }
                        if ps.axes
                        else None
                    ),
                }
            )
        records.append(
            {"trace_id": trace.trace_id, "source": trace.source, "steps": steps_out}
        )

    total = n_auto + n_human + n_majority + n_inadmissible + n_no_verdict
    summary = {
        "traces": len(raw_traces),
        "steps": total,
        "auto_unanimous": n_auto,
        "human_needed": n_human,
        "auto_majority_provisional": n_majority,
        "inadmissible": n_inadmissible,
        "no_verdict_all_judges_abstained": n_no_verdict,
        "rubric_review_candidates": n_rubric,
        "human_fraction": round(n_human / total, 3) if total else 0.0,
        "judges": [getattr(j, "name", "judge") for j in judges],
        "source_families": sorted({_judge_family(j) for j in judges}),
        "min_families": min_families,
    }
    return records, summary
