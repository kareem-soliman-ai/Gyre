# Gyre's Major Lessons

This is the compact map. Each lesson links to executable evidence or the
document that carries its full qualification boundary.

## 1. A loop is a controller, not a prompt with repetition

A useful loop has a controlled variable, an observation, a sensor, a decision
rule, an action menu, terminal states, and a budget. “Keep improving until
done” supplies none of those.

For a graph, apply the same rule to every conditional edge:

```text
state -> observation -> sensor -> policy -> next node
```

Try: `python scripts/loop_playground.py --list`

Go deeper: [Architecture](architecture.md) and
[loop-and-graph engineering](loop-and-graph-engineering.md).

## 2. Measurement quality and control quality are separate questions

A good policy cannot rescue a bad sensor. A better sensor does not prove the
policy uses it well. A successful system does not identify which component
caused success.

Evaluate three links separately:

1. **Link A:** does the measurement track an independent criterion?
2. **Link B:** does the policy choose well with the measurement held fixed?
3. **Link C:** does the complete system improve objective outcome under a
   matched budget?

Go deeper: [Measurement for Loop Engineering](measurement-for-loop-engineering.md).

## 3. Plausible labels and pooled scores can conceal invalid measurement

Repository evidence showed two recurring traps:

- a pooled score can hide catastrophic performance on the cell where false
  alarms are most costly;
- a construct-blind surface rule can agree with labels because the labels and
  sensor share the same method, not because either measures the construct.

Ask for cell-level results, independent criteria, adversarial controls, and
falsifiers.

Try:

```bash
python -m gyre.lessons 1
python -m gyre.lessons 3
```

Evidence status: executable synthetic-corpus results. They establish the local
failure mechanism, not real-world prevalence.

## 4. Measurement does not always pay

A competently tuned blind or fixed policy can beat a sensed policy in some cost
regimes. The defensible benefit of measurement may be robustness across
regimes rather than peak performance in one chosen setting.

Always compare against:

- a strong blind heuristic;
- a fixed weak or low-disturbance policy;
- no-probe or renewable-negative-control conditions; and
- an oracle-signal cell that can reveal a policy bottleneck.

Try: `python -m gyre.lessons 2`

Evidence status: executable synthetic control regimes. The result falsifies
“measurement must always help.”

## 5. Observing and verifying can change the world

An active measurement may:

- move the measurand;
- change how later controls act;
- bias later observations;
- consume time or future optionality; or
- change a human's attention, confidence, or behaviour.

Therefore a sensor may also be an action node in the causal graph. Estimate
information value and observer disturbance separately.

Try:

```bash
python scripts/living_factory.py --demo
python scripts/alien_factory.py --demo
python scripts/observer_effect_playground.py
```

Evidence status: [EXP-06](../experiments/EXP-06_MeasurementInterferenceQualification_2026-07-28/results/ANALYSIS.md)
qualified local mechanics and generous-budget identifiability. It did not
qualify the final budgeted challenge or establish external transfer.
[EXP-07](../experiments/EXP-07_LivingInstrumentExpeditionQualification_2026-07-29/results/ANALYSIS.md)
removed the idle exploit but found a 200/200 fixed-policy ceiling.
[EXP-08](../experiments/EXP-08_LivingInstrumentExpeditionRecovery_2026-07-29/results/ANALYSIS.md)
reduced that baseline to 99/200, but its preregistered omnibus gate still did
not pass.

## 6. Names are hypotheses, not hidden answer keys

Unknown phenomena need immutable machine IDs. Humans and systems may attach
revisable names, explanations, and confidence estimates, but objective scoring
must depend on predictions and outcomes rather than preferred vocabulary.

```text
identity:   xeno-17
alias:      "scan-reactive flock"
hypothesis: "active scans increase its presence" (0.65)
criterion:  what happens after the next declared scan
```

Two participants can use different words and discover behaviourally equivalent
models. The Alien Factory enforces this separation in code.

## 7. A useful category explains most cases, not every case

A category should compress causal structure without pretending its members are
identical. Gyre v2.2.1 uses a three-level construction:

```text
family -> variant tendency -> persistent unit deviation
```

Three of four units follow each variant's majority weather response. One is a
stable exception. The label therefore supports action, while unit identity
still rewards observation and memory.

EXP-09 showed the opposite failure mode. Within-variant differences were
learnable, but variant and context explained only 43.17% of effect variance.
EXP-10 increased only between-variant separation. The recovered model explained
62.11%, while stable unit identity added 37.89 percentage points. Minimum
within-variant SD remained 0.0736.

Those values come from terminal revealed profiles. They establish the
construction's variance structure, not budgeted recoverability by a player.

The residual must persist. Fresh randomness creates uncertainty without
creating knowledge a controller can accumulate.

Try: `python scripts/hierarchical_factory.py --demo`

Evidence status: synthetic mechanics on reused public development seeds.
EXP-10 passed its recovery gates but is not independent confirmation.

## 8. Humans and systems are both fallible sensors and controllers

A human judgement is evidence with a scope, criterion, confidence, confounds,
and possible calibration history. An AI judgement has the same obligations.
Neither confidence nor authority proves capability.

Keep five constructs separate:

1. objective task outcome;
2. human acceptance;
3. human capability;
4. system capability; and
5. joint capability.

Assign authority per decision. Prefer human ownership when consequence and
unresolved ambiguity are high or task-local human evidence is stronger.
Permit autonomous system action when it is reversible, independently
verifiable, within authority, and supported by stronger task-local evidence.

Go deeper: [First-principles reciprocal control](first-principles-loop-control.md).

## 9. A human should receive a control menu, not only approve or reject

Useful options include requesting evidence, choosing an alternative, revising
the criterion, changing authority, delegating bounded work, pausing an action,
or terminating the goal.

A human choice changes the route. It is not proof that the route was correct.
Routine recoverable details should remain autonomous rather than repeatedly
interrupting the human.

Try:

```bash
python scripts/loop_playground.py --case accepted-but-objectively-failing
python scripts/loop_playground.py --case verifier-drift --level builder
```

## 10. Objective outcomes and preference outcomes must remain separate

Human acceptance is the correct target for preference or consent. It is not an
objective correctness label. Where possible, use frozen tests, authoritative
sources, blinded adjudication, or delayed real-world results as independent
outcome criteria.

Joint capability requires a matched comparison:

```text
joint gain = team outcome - max(human-only outcome, system-only outcome)
```

One strong team result does not establish complementarity.

Go deeper: [Joint Capability Challenge](joint-capability-challenge.md).

## 11. Public method and protected instruments can coexist

The public repository should make the argument runnable:

- interfaces and naive baselines;
- teaching worlds and visible tests;
- experiment designs, receipts, nulls, and failed gates;
- validators and framework-neutral contracts.

The defensible protection boundary is:

- fitted operating points;
- private calibration data and corpora;
- protected instrument implementations;
- user capability profiles; and
- learned controller parameters.

This is not “trust the secret.” Public challengers must be able to substitute
their own sensors and controllers and compare objective results.

## Evidence status at a glance

| Surface | Current status |
|---|---|
| Loop catalogue | Documented design patterns; maturity stated per pattern |
| Naive sensors and benchmark | Runnable public baselines |
| Executable lessons 1-3 | Local synthetic evidence |
| `loop-engineer` skill | Public design hypothesis; qualification gates did not pass |
| `compile-joint-control` skill | Experimental; qualification gates did not pass |
| Sealed Repository Rescue scorer | Engineering sub-gate passed; public benchmark gates remain |
| Alien Factory mechanics | EXP-06 mechanics and identifiability gate passed |
| Living Instrument Expedition v2.0 | EXP-07 idle exploit removed; difficulty gate failed |
| Living Instrument Expedition v2.1 | EXP-08 recovery discriminated mission outcome; omnibus gate failed |
| Hierarchical Expedition v2.2 | EXP-09 persistent heterogeneity worked; variant-model gate failed |
| Hierarchical Expedition v2.2.1 | EXP-10 passed 11/11 reused-development recovery gates |
| Post-freeze adaptive challenge | Not yet qualified |
| Real-world joint-capability improvement | Not established |

The [experiment index](../experiments/INDEX.md) is the canonical receipt list.
