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
import os
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
{"is_ruminating": true|false, "confidence": 0.0-1.0, "rationale": "one sentence"}
"""


@dataclass
class JudgeVerdict:
    is_ruminating: bool
    confidence: float = 0.5
    rationale: str = ""


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
    ) -> None:
        self.name = f"judge:{model}"
        self.model = model
        self._key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self._rubric = rubric
        self._context_window = context_window
        self._endpoint = endpoint
        self._timeout = timeout

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
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        return _parse_verdict(content)


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
            )
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    # Fallback: no parseable verdict. Default to not-ruminating, low confidence.
    return JudgeVerdict(is_ruminating=False, confidence=0.0, rationale="unparseable judge output")


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


def qualify_judge(
    judge_labels: Sequence[bool],
    human_labels: Sequence[bool],
    *,
    judge_name: str = "judge",
    kappa_floor: float = 0.6,
    ac1_floor: float = 0.6,
) -> JudgeQualification:
    """Decide whether a judge agrees with humans well enough to scale the corpus.

    A judge qualifies only if BOTH Cohen's kappa and Gwet's AC1 clear their floors.
    Requiring both guards against two failure modes at once: a judge that agrees
    only by matching the majority class (AC1 catches inflated raw agreement; kappa
    catches nothing here, which is why AC1 is in), and one that looks good on kappa
    but is unstable under the real base rate. Floors default to 0.6 (substantial
    agreement); raise them for higher-stakes use.
    """
    if len(judge_labels) != len(human_labels):
        raise ValueError("judge_labels and human_labels must be the same length")
    kappa = cohen_kappa(judge_labels, human_labels)
    ac1 = gwet_ac1(judge_labels, human_labels)
    raw = sum(1 for x, y in zip(judge_labels, human_labels) if x == y) / len(human_labels)
    reasons: list[str] = []
    if kappa < kappa_floor:
        reasons.append(f"cohen_kappa {kappa:.2f} below floor {kappa_floor}")
    if ac1 < ac1_floor:
        reasons.append(f"gwet_ac1 {ac1:.2f} below floor {ac1_floor}")
    qualified = not reasons
    if qualified:
        reasons.append("clears kappa and AC1 floors")
    return JudgeQualification(
        judge=judge_name,
        n=len(human_labels),
        raw_agreement=raw,
        cohen_kappa=kappa,
        gwet_ac1=ac1,
        positive_rate_human=_rates(human_labels),
        positive_rate_judge=_rates(judge_labels),
        qualified=qualified,
        reasons=tuple(reasons),
    )
