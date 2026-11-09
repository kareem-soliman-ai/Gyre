# Alien Factory: When the Probe Changes the World

## Play first

```bash
python scripts/alien_factory.py
```

Factory Kestrel is being established on an uncharted continent. Hurricane Ilex
arrives after 18 actions. Three unknown phenomena cross the site. Participants
receive stable machine IDs, but no authoritative semantic names. They can
assign and revise aliases and hypotheses as evidence accumulates:

```text
xeno-17
  alias: "scan-reactive flock"
  hypothesis: "active scans increase its presence"
  confidence: 0.65
```

The evaluator never scores those words. It scores the terminal latent states
after observation and control. In the teaching mission, survival requires every
absolute terminal state to be at most `0.5`, and the stability score is:

\[
100\exp(-3\,\mathrm{mean}(x_i^2))
\]

Probe count, disturbance, and remaining time are reported separately rather
than folded into that score.

## Objective

Turn a neglected loop-engineering failure mode into a public, runnable
expedition: measurement may alter the object, the controller-facing causal
mechanism, or the accuracy of later measurements.

This is the difference between:

```text
observe -> decide -> act
```

and:

```text
observe ─┬─> decide -> act
         ├─> change the measurand
         ├─> change how later actions work
         └─> change what later observations report
```

A loop that assumes the first graph while inhabiting the second can become less
accurate each time it checks itself.

The narrative is functional rather than cosmetic. The factory supplies a
controlled objective, the hurricane supplies a finite horizon, the unknown
continent removes familiar domain labels, and the phenomena make adaptation
and observer effects legible. Participant-created names remain hypotheses
rather than hidden benchmark answers.

## Methodology

Gyre implements a dependency-free scalar world in
[`gyre.challenge.observer_effects`](../src/gyre/challenge/observer_effects.py).
An active probe reads first and then applies a signed, intensity-dependent
effect to any combination of three paths:

| Path | What changes | Loop failure if ignored |
|---|---|---|
| measurement to measurand | the latent state being controlled | the reading is already stale because taking it moved the target |
| measurement to mechanism | the gain of later control actions | a previously correct action magnitude overshoots or undershoots |
| measurement to future measurement | accumulated active-instrument bias | repeated checks appear to confirm a change the instrument created |

The included response families are linear, saturating, and thresholded.
Coefficients may be positive, negative, null, balanced, or dominated by one
path. Probe intensity is a controller choice in `[0, 1]`.

A `REFERENCE` probe is a renewable negative control. It observes the latent
state without applying the active intervention and without inheriting the
active instrument's accumulated bias. It is intentionally powerful: the
standard challenge is about experimental design under an information budget,
not guessing that an observer effect exists.

The twin helper uses common random noise to qualify simulator mechanics. It is
an evaluator tool, not participant evidence.

## Results

### What should be known?

Use three disclosure modes:

| Division | Public information | Hidden information | Purpose |
|---|---|---|---|
| Tutorial | exact profile and response curve | seeds and future states | learn the causal accounting |
| Standard | observer effects are possible; candidate paths and family set; a discoverability guarantee | active paths, coefficients, signs, severity, curve, seeds | fair scientific discovery and control |
| Blind research | no observer-effect warning | everything | estimate how often controllers discover model misspecification unaided |

The standard division should not conceal the possibility itself. A contestant
who never considers observer effects would then be indistinguishable from one
who considered them but rationally declined an expensive test. Performance
would partly measure familiarity with the benchmark author's trick.

Instead, disclose the model class and hide the realised world. This preserves
difficulty because the controller must still decide:

- whether the effect is material;
- which path or paths are active;
- the sign and magnitude of each effect;
- which response family fits;
- whether the reference is sufficiently reliable;
- how much probing is worth its interference, cost, and lost time; and
- when residual ambiguity requires a robust action rather than a point
  estimate.

### Qualification evidence

[EXP-06](../experiments/EXP-06_MeasurementInterferenceQualification_2026-07-28/results/ANALYSIS.md)
tested ten frozen profiles. An interaction-only baseline recovered all 9
identifiable response families, reached coefficient MAE 0.003319, and reduced
aggregate terminal MSE from 0.044444 under a passive-measurement assumption to
0.000947. It came within 4.8% of the exact-prior policy.

That baseline used 720 calibration readings per profile. The experiment proves
discoverability under generous evidence, not competitive difficulty.

### Scoring

Do not collapse everything into one opaque reward. Report:

1. terminal objective error on untouched worlds;
2. intervention burden caused by measurement;
3. active and reference probe counts;
4. recovery error for the hidden causal profile, when an estimate is submitted;
5. wall time, human time, model cost, and tokens; and
6. hard-constraint violations separately.

Rank terminal outcome under a fixed information budget, then report the
non-dominated efficiency frontier. A controller that reaches the same outcome
with fewer or weaker probes should remain visibly better.

### Harder, still fair

Difficulty should come from controlled causal variation, not obscurity:

- give different paths different response families;
- delay an effect by one or more actions;
- let effects decay, accumulate, or exhibit hysteresis;
- vary whether the reference probe is renewable, exhaustible, or mildly
  reactive, while declaring that class;
- couple mechanism gain to measurand region;
- include weak-identification cells where several profiles remain plausible;
- corrupt a subset of reference probes and require uncertainty reporting;
- place probe costs and deadlines on an explicit budget;
- generate the active profile only after the submitted controller is frozen.

Every final world should have an identifiability audit. If two materially
different hidden worlds are observationally equivalent under the allowed
budget but require different optimal actions, the scorer must accept a robust
set-valued answer or label the cell ambiguous. It must not quietly grade one
unrecoverable secret as correct.

## Discussion

This machinery changes loop engineering in two ways.

First, sensors become actions. Graph specifications need intervention edges
from measurement nodes back into state, mechanism parameters, and instrument
state. Probe choice belongs in the controller policy, with intensity, cost, and
expected future information recorded.

Second, verification is no longer automatically benign. More checks can reduce
uncertainty while worsening the state or degrading future evidence. A good loop
therefore estimates both information value and observer tax, compares a
renewable negative control, and preserves a no-probe baseline.

The same design supports human-AI teams. A human can propose competing causal
explanations, choose which ambiguity matters, or recognise domain-specific
observer effects. A system can run calibration interactions, fit curves,
maintain uncertainty, and execute low-consequence probes. Their joint outcome
is objectively scored against the untouched terminal state rather than judged
by whether the collaboration looked persuasive.

## Next Steps

The public simulator and qualification baseline are open method. Future
leaderboard profiles, final seeds, fitted high-performing policies, and any
validated proprietary measurement instruments can remain behind the existing
provider/controller seam.

The constants in the teaching world are authored synthetic fixtures, not fitted
instrument parameters. They are safe to inspect after a run and must not be
presented as ecological or behavioural estimates.

The next experiment should reduce the 720-reading calibration allowance,
preregister a strong fixed-weak baseline, and measure the outcome/probe
efficiency frontier under delayed and path-specific nonlinear interference.
