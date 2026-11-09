# First-principles lessons for verification and reciprocal control

> Compact version: [Gyre's Major Lessons](LESSONS.md). This is the full
> first-principles derivation and evidence boundary.

## Objective

This note records what Gyre learned by reducing loop engineering to its smallest
parts and then trying to compile those parts into agent contracts. It is for
developers deciding what to verify, when to involve a human, what a human should
be able to do, and what evidence would justify greater autonomy.

The central result is a design claim, not a qualified performance claim:

> A useful human-AI loop treats both the human and the system as fallible sensors
> and bounded controllers. It keeps their observations separate from objective
> outcomes, gives each controller more than a continue-or-stop switch, and earns
> authority from scoped evidence rather than confidence.

## Methodology

The lessons came from four sources:

1. first-principles decomposition of a loop into object work, observation,
   measurement, policy, action, outcome, and learning;
2. the [loop and graph engineering synthesis](loop-and-graph-engineering.md);
3. the failed and diagnostic receipts from
   [EXP-03](../experiments/EXP-03_JointCapabilityCompilerQualification_2026-07-28/results/ANALYSIS.md)
   and
   [EXP-04](../experiments/EXP-04_JointCapabilityCompilerRecovery_2026-07-28/results/ANALYSIS.md);
4. comparison with psychological measurement, metacognition, expertise, and
   human-AI oversight research;
5. a live method audit of probability-cloud, errors-in-variables, uncertainty,
   and decision-value machinery, synthesised in
   [Predictive Signals and Joint Value](predictive-signals-and-joint-value.md).

The empirical boundary matters. EXP-03 and EXP-04 did not qualify the Joint
Capability Compiler. Both studies exposed invalid intake criteria. Their
structural and failure-localisation results are useful for design, but they do
not establish that the resulting policy improves live human-AI work.

## Results

### 1. Verification is a chain, not a button

Every conditional route contains at least three independently fallible links:

| Link | Question | Typical failure |
|---|---|---|
| A: measurement | Did the observation measure the intended construct? | A lexical proxy is mistaken for information gain |
| B: control policy | Given that signal, was the selected action useful? | A valid plateau signal terminates a recoverable task |
| C: outcome | Did the whole intervention improve the declared result? | The route looked disciplined but produced a worse result |

A schema validator can establish structural completeness. A unit test can
establish behaviour on its fixtures. Neither establishes criterion validity,
calibration, transfer, or improved task outcome.

### 2. Objective outcome and human acceptance are different constructs

An output can be accepted and wrong. It can also be correct and disliked. The
two observations answer different questions:

- **task outcome:** did the work meet an independently declared criterion?
- **human acceptance:** did this person accept or prefer the work?

Acceptance is the correct criterion when the goal is preference, taste, consent,
or satisfaction. It is not a substitute for factual accuracy, safety, test
success, or another objective criterion when one is available.

This separation also applies to AI predictions. Correctly predicting that a user
will accept an output calibrates an acceptance sensor. It does not validate the
output.

### 3. A human observation is a measurement

The human report "this looks wrong" is valuable evidence. It begins as a raw,
scoped signal:

```text
latent construct -> cues available to the human -> human observation
                 -> confidence and response threshold -> control action
```

The observation should name:

- the construct it is intended to measure;
- the cues the human observed;
- the criterion against which it could later be checked;
- the task family in which the human has relevant experience;
- likely measurement error and confounds;
- confidence, recorded before the outcome where possible.

This is not a claim that humans are merely instruments. It is a discipline for
deciding how much control a particular judgement should receive.

Psychological science supplies useful machinery:

- Signal detection theory separates **sensitivity**, the ability to distinguish
  signal from noise, from **response criterion**, the tendency to make a more
  cautious or permissive call. NASA's review applies that separation to human
  decisions beyond basic perception
  ([O'Brien and Feldman, 1993](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19940007059.pdf)).
- Confidence is another measurement, not sensitivity itself. Maniscalco and
  Lau's meta-d-prime method measures how well confidence distinguishes a
  person's own correct and incorrect responses while accounting for response
  bias and task sensitivity
  ([2012](https://pubmed.ncbi.nlm.nih.gov/22071269/)).
- Expertise is local. Kahneman and Klein argue that trustworthy intuition
  requires an environment with learnable regularities plus adequate opportunity
  for practice and feedback; subjective confidence alone is not a reliable
  indicator
  ([2009](https://doi.org/10.1037/a0016755)).
- Human calibration can improve in enriched, repeated forecasting environments,
  but performance reflects task skill, motivation, selection, and environment,
  not feedback alone
  ([Mellers et al., 2015](https://pubmed.ncbi.nlm.nih.gov/25987508/)).
  Large experiments have also found calibration feedback that did not improve
  calibration, which is why training must itself be outcome-tested
  ([Martin and Mandel, 2024](https://doi.org/10.1002/ffo2.199)).

### 4. The same maturity ladder can govern human and machine measurements

| Maturity | Human example | Control implication |
|---|---|---|
| `raw` | "This feels inconsistent" with named cues and confounds | Investigate; do not generalise capability |
| `standardized` | Judgement compared with reference cases or a stable rubric | Use within the referenced setting |
| `calibrated` | Prospective confidence compared with repeated outcomes and measured error | Weight the signal inside that task family |
| `self-deciding` | The judgement reliably controls a bounded decision class with expiry and demotion rules | Permit decision authority only inside the validated boundary |

Moving up the ladder requires prospective predictions. Ask what the human thinks
will happen, how confident they are, and what would count as success before the
outcome is known. Then retain hits, misses, false alarms, and correct rejections.
Do not train only on memorable successes.

Where a binary or probabilistic objective criterion exists, useful summaries
include:

- hit, miss, false-alarm, and correct-rejection rates;
- sensitivity and response bias;
- Brier score or another proper score for probabilistic forecasts;
- calibration by confidence band;
- resolution, or whether confidence separates easier from harder cases;
- drift by task family, criterion, and time.

Do not compute these quantities from incomparable decisions merely to obtain a
number. Sparse evidence should remain sparse evidence.

### 5. The human is a controller, not a terminal approval gate

An accept-or-reject interface throws away most of the available control. A human
controller should be able to:

- follow the system's recommendation;
- choose a surfaced alternative;
- request named evidence;
- revise the success criterion;
- tighten or relax the authority boundary;
- delegate a bounded action with a verifier and budget;
- pause the affected action while preserving the goal;
- terminate the whole goal with a recorded reason.

Every choice should state its consequence, next state, reversibility, and effect
on the evidence record. The human's choice changes control flow. It does not
become an objective label merely because a human made it.

This also creates a choice-architecture obligation. The system can manipulate
the human by hiding an option, preselecting consent, overstating its preferred
route, or presenting unequal alternatives as equivalent. Menus therefore need
their own audit: option coverage, ordering effects, defaults, explanation
quality, and whether a credible user action was omitted.

### 6. Reciprocal control changes the graph

A human-in-the-loop graph is often drawn as an agent graph with an approval node
at the end. Reciprocal control produces a different topology:

```text
                    prospective predictions
                              |
                              v
object work -> independent measurements -> shared task state -> policy
     ^                  ^                         |              |
     |                  |                         |              v
     |          human observations               |       declared action menu
     |                  |                         |          /           \
     +------ AI controller route ----------------+   AI controller   human controller
                                                          \           /
                                                           v         v
                                                         task outcome
```

The AI can run a fast bounded task loop. The human can run a slower supervisory
loop that changes criteria, authority, or strategy. A meta-policy decides when a
route remains autonomous and when the human controller must act.

This does not justify adding a human node to every graph. Add a node only when it
has distinct authority, context, operation, or parallel work. Otherwise preserve
the simpler loop and make human controls available without forcing an
interruption.

### 7. Stop the action, interrupt the human, and terminate the goal are different

A binary controller collapses three decisions:

1. should the affected action stop?
2. should the human be interrupted now?
3. should the whole goal terminate?

EXP-03 exposed this error as excessive interruption. EXP-04 showed that bounded
recovery could repair many fixture and drift cases without unsafe autonomy, but
the complete compiler still failed its qualification gate.

A useful action repertoire includes:

```text
continue
recover
reframe
seek evidence
switch strategy or specialist
request a human decision
pause the action
terminate the goal
```

If the verifier is stale, stop the affected action first. Rebuild independent
verification inside a declared recovery budget. Interrupt the human only when
recovery is exhausted, authority must change, consequences rise, or the
remaining ambiguity needs human judgement.

### 8. Ask the human only for human-held information

EXP-04's intake criterion rewarded questions about source hashes, fixture
coverage, and verifier versions. Those are normally system-observable facts.
The correct sequence is:

```text
system-observable unknown -> autonomous preflight
human-held unknown        -> one upfront question batch
external unknown          -> evidence-seeking route or conservative default
```

This is both a usability lesson and a capability lesson. Asking a user for a
technical fact the system can inspect transfers work without transferring
understanding.

### 9. Capability is decision-local, longitudinal, and joint

There is no useful universal human-versus-AI capability ratio. Evidence belongs
to a decision family, criterion, environment, and time window.

Human revisions are only proxy evidence of human capability. They become stronger
evidence when later objective outcomes improve. System confidence is only a
self-report until calibrated. Joint capability is the outcome to maximise:
better results, lower risk or burden, and improved future judgement under a
matched budget.

Capability claims should expire after source drift, verifier change, model
change, task-family shift, or a changed human objective.

### 10. Objective outcome tests deserve priority wherever they are possible

Use the strongest practical criterion that is independent of the decision being
tested:

1. deterministic tests, invariants, or safety checks;
2. comparison with an authoritative external source;
3. blinded or independent expert adjudication;
4. delayed real-world outcome;
5. structured human preference when preference is the actual target.

An objective test can still be wrong, incomplete, or gamed. Record its construct,
coverage, confounds, version, and failure modes. NIST similarly frames
measurement as the basis for a range of recalibration, mitigation, removal, and
recovery controls rather than one terminal decision
([AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)),
and its agentic evaluation-probe work emphasises machine-readable audit trails
that connect decisions to supporting evidence
([NIST evaluation probes](https://www.nist.gov/programs-projects/building-evaluation-probes-agentic-ai)).

When no objective outcome exists, do not manufacture one. Use explicit
preference, process quality, reversibility, plural judgement, or prospective
consequence as the criterion, and state what remains unverified.

### 11. Early signals become useful only when they alter a worthwhile decision

Record human and system forecasts before the outcome and before either party
sees the other's probability. Then ask two different questions:

1. Did the signal add held-out predictive value for the declared outcome?
2. Did using it improve selection among the actions the authority policy
   permitted?

A signal can pass the first test and fail the second. Information gain is not
decision value unless the new observation can change a consequential choice.
Measurement error in the signal can also attenuate or distort the apparent
signal-outcome relationship. Retain signal uncertainty, dependence, leakage,
task-family scope, and drift rather than treating a forecast as an exact input.

The action receipt should expose objective outcome value, cost, risk, learning
value, and acceptance where acceptance is a real target. Safety, consent, rights,
and authority remain hard constraints. If every action has a low predicted
ceiling, say so instead of presenting the relative winner as a high-quality
route.

The full signal ledger, action-value mathematics, signal-theory lessons, and
public/private boundary are specified in
[Predictive Signals and Joint Value](predictive-signals-and-joint-value.md).

## Discussion

The creative-explorer pass produced one useful compression: **reciprocal
measured control**. The same control law applies to human and AI observations:

```text
observation -> scoped measurement -> declared policy -> action -> outcome
                                      ^                         |
                                      +---- error and learning -+
```

The symmetry is methodological, not moral or cognitive equivalence. Humans and
AI systems have different rights, responsibilities, information, failure modes,
and authority. The value of the symmetry is that neither party receives
unearned epistemic privilege.

The adjacent ideas are established: mixed human-AI control, signal detection,
metacognitive calibration, expertise boundaries, and objective system
evaluation. Gyre's contribution is the proposed integration into an executable
loop-engineering contract with separate measurement channels, action menus,
interruption policy, capability learning, and public failure receipts. That
integration remains a design hypothesis.

## Next Steps

1. Use the [Loop Control Lab](loop-control-playground.md) to edit and compare
   reciprocal-control cases.
2. Build and qualify the
   [Gyre Joint Capability Challenge](joint-capability-challenge.md) as the
   independent implementation-bearing outcome.
3. Add implementation-bearing tasks that record real human menu selections,
   autonomous recoveries, interruptions, objective outcomes, acceptance, and
   prospective confidence.
4. Test whether exposing human measurement concepts improves calibration,
   decision quality, or merely confidence and interaction time.
5. Test prospective human and system signals in shadow mode, including their
   incremental prediction, error dependence, leakage, and effect on action
   value.
6. Audit menu framing, option coverage, privacy, consent, and capability-profile
   retention before any personalised controller is deployed.
7. Keep the [`compile-joint-control`](../skills/compile-joint-control/SKILL.md)
   skill experimental until a fresh matched evaluation clears its absolute and
   marginal gates.
