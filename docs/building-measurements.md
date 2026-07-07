# Build Your Own Measurement

The loops in Gyre are controllers. A controller needs a sensor, and the sensor is
the part that decides whether the whole thing works. This guide is for building
that sensor: a `MeasurementProvider` that reads an agent's behaviour and reports
on the loop's health.

Two honest promises up front. First, the easy version is genuinely easy, and this
guide will get you there fast. Second, the hard version is genuinely hard, and
this guide will show you exactly where it gets hard and why, because that boundary
is the most useful thing you can learn from this project. If you finish this guide
thinking "measurement is a bigger discipline than I assumed," it did its job.

## The interface

A provider is one small protocol:

```python
from gyre.measurement import Meaning, Measurement, MeasurementProvider

class MyProvider:
    loop_id = "L1"                 # which loop's construct you measure
    name = "mine:my-provider"      # for provenance and the benchmark

    def measure(self, observation) -> Measurement:
        ...                        # read the observation, return a Measurement

    def reset(self) -> None:
        ...                        # clear any state for an independent run
```

That is the whole contract. Everything hard lives inside `measure`, which is the
point: the interface is free and obvious, and the quality of what you put behind
it is the entire game.

Wire it into a loop and you are done:

```python
from gyre import RuminationMonitor
monitor = RuminationMonitor(MyProvider(), patience=3, threshold=0.2)
```

## The Measurement you return, and the ladder inside it

This is the most important idea in the guide. A `Measurement` has two required
fields and several optional ones, and **the optional ones are a maturity ladder**.
How many you can honestly fill tells you, and the loop, how good your sensor is.

```python
Measurement(
    value=0.03,                          # required: the raw reading
    meaning=Meaning.HIGHER_IS_HEALTHIER, # required: which direction is healthy
    # --- the ladder (optional; fill what you can honestly support) ---
    standardized=-2.4,                   # reading relative to a modelled baseline (a z-score)
    probability=0.88,                    # calibrated P(pathological state)
    decision=True,                       # your own fire/hold call, if you've earned it
    measurement_error=0.05,              # your estimate of your OWN reliability
    # --- always ---
    confounds=("lexical, not semantic",),# how this reading can mislead. Never hide these.
    provider=self.name,
)
```

- Fill only `value` + `meaning`: you have a **raw proxy**. The loop is forced to
  apply a threshold *you* supply, and you have given it no sense of how noisy the
  reading is. This is where the naive baselines sit, honestly.
- Fill `standardized`: you **model a baseline**, so you can say how far from normal
  this reading is, not just how big it is. The loop stops needing a hand-set
  threshold and can fire at a principled number of standard deviations.
- Fill `probability`: you are a **calibrated classifier** of the latent state.
- Fill `decision`: you have **validated** enough to make the call yourself, so the
  loop can defer to you.
- Fill `measurement_error`: you estimate your **own reliability**. This is the
  psychometric signature. A diff ratio will never give it to you. A fitted
  latent-variable model can, and that difference is not cosmetic.

You are not required to climb the ladder. You are required to be honest about
which rung you are on. Leaving a field `None` is not a defect; claiming a rung you
have not earned is.

## The four design considerations that actually matter

### 1. You are measuring a latent construct, not a surface

"Is this loop ruminating" is not something you can read off the trace. It is a
hidden property you infer from a proxy. The proxy is not the construct. Diff
novelty is a proxy for information gain; it is not information gain. The moment you
forget this, you start trusting the proxy where it diverges from the thing you
care about, and it always diverges somewhere.

The discipline that studies this is **construct validity**: the question of whether
your measure actually captures the construct it claims to, rather than something
correlated with it that comes apart under pressure. Before you ship a measure, ask:
what is the construct, what is my proxy, and where do they part ways? If you cannot
answer the third part, you do not yet understand your own measure.

### 2. Name your confounds, because they are the failure modes

Every proxy is confounded, and the confounds are not footnotes, they are the exact
conditions under which your sensor lies. The `confounds` field exists to force you
to enumerate them. Diff novelty rewards thrashing and is fooled by renaming. A
rolling Brier has no reliability and no over/under-confidence sign. A single
Gaussian baseline is wrong for a bursty channel. Write these down, because a
downstream loop weighting your signal needs to know them, and because writing them
down is how you discover your measure is worse than you hoped.

### 3. Reliability is a number, and it should be yours to report

There is a difference between "the loop is ruminating" and "the loop is ruminating,
and I am 90% reliable when I say that." The second is a measurement; the first is
an opinion. Reliability is estimable: run your sensor twice on the same input and
see if it agrees with itself (test-retest); check whether independent versions of
it agree (inter-rater); model the error on your estimate directly. If your sensor
can report its own `measurement_error`, a loop can weight it, discount it when it
is shaky, and trust it when it is sure. This is the single biggest thing that
separates a metric from an instrument.

### 4. A measure that has not been validated cannot make a claim

You can build a rumination detector in an afternoon. You cannot know whether it
works until you have run it against traces a human has labelled and checked that
its scores track the labels. Until then it is a hypothesis with a decimal point.
This is not bureaucracy; it is the difference between a number you can act on and a
number that will quietly mislead you. Gyre ships a harness for exactly this check.

## Prove it: `gyre.bench`

Do not argue about whether your measure is good. Measure it.

```python
from gyre.bench import LabelledTrace, compare_providers
from gyre.providers import DiffNoveltyProvider

traces = [LabelledTrace(observations=..., labels=..., loop_id="L1")]
for score in compare_providers([DiffNoveltyProvider(), MyProvider()], traces):
    print(score.provider, score.f1, "calibrated" if score.calibrated else f"swept θ={score.best_threshold}")
```

The harness scores each provider against labelled traces. If your provider makes
its own decisions it is scored on those; if it only returns raw values, the harness
sweeps a threshold and hands it its *best-case* F1 in hindsight, which is generous,
and it still usually trails a sensor that models the construct. Two things to read
off the result:

- **Did it need a swept threshold?** If yes, you would not know that threshold in
  production. That is a real cost the F1 number hides.
- **How big is the gap to the baseline?** If your careful measure barely beats diff
  novelty, either the construct is easy (fine, use the cheap one) or your measure is
  not yet capturing what the baseline misses (back to construct validity).

One caveat the harness cannot fix for you: it is only as honest as your labels.
Agreement with bad labels is worthless. Building a defensible labelled corpus is
itself real work, and a separate thing from building the detector.

## Where naive is enough, and where it is not

This project is not an argument that all measurement must be elaborate. It is an
argument that measurement is a discipline, and part of the discipline is knowing
when the cheap proxy suffices.

- **Naive is often enough** for low-stakes, high-signal cases: an agent stuck in a
  literal identical-retry loop, a numeric channel with a clean single-mode
  baseline, a coarse "is anything changing at all" gate. Use the naive baselines
  and move on. Do not gold-plate a measurement whose errors do not cost you
  anything.
- **Naive is not enough** where the construct is subtle and the errors are
  expensive: rumination hidden under lexical novelty, calibration where
  overconfidence and underconfidence need different responses, rupture in a
  human-agent dyad where a false alarm trains the human to ignore you. These are
  latent constructs measured from noisy behaviour, and a proxy that does not model
  the construct will fail in ways you cannot see from the number. This is the
  regime where measurement stops being a weekend job.

The value of a measurement is not its sophistication. It is the match between how
hard the construct is and how hard the measure works. Knowing that match is the
skill.

## Pointers for going deeper

If considerations 1 through 4 landed and you want the field that owns them, the
keywords are: **construct validity** and **criterion validity** (does your measure
capture the thing, and does it predict what it should), **reliability** (test-retest,
inter-rater, internal consistency), **latent-variable modelling** and **factor
analysis** (estimating a construct you cannot observe from indicators you can),
**errors-in-variables** and **attenuation** (what measurement noise does to any
correlation you compute downstream, and how to correct it), and **calibration**
(Brier score, reliability diagrams, proper scoring rules). This is psychometrics,
and it is a century deep. The loops are the easy half of Gyre on purpose. This is
the half where the depth is.

If you build something here that beats the baselines on real labelled traces, that
is a genuine contribution and the [contributing guide](../CONTRIBUTING.md) wants it,
with one firm rule: no performance claim ships without the validation behind it. See
[measurement-stance.md](measurement-stance.md).
