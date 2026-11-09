# The Gyre Joint Capability Challenge

> **Research-track status:** this document specifies the Sealed Repository
> Rescue outcome instrument and matched human/system protocol. It is not the
> five-minute entry point. Start with the
> [Alien Factory expedition](observer-effects-challenge.md); use this document
> when studying objective joint-capability comparisons and scorer fairness.

## Objective

Create one externally scored task family on which humans, systems, and
human-system teams can compete using any measurement, controller, graph, or loop
they choose.

The task must satisfy two different goals:

1. produce a fair, verifiable **external outcome score** for a completed attempt;
2. support a defensible **joint-capability proxy** by comparing a team with its
   human-only and system-only constituents under matched conditions.

The recommendation is:

> [PLAUSIBLE] Build a **Sealed Repository Rescue** challenge. Give each entrant
> a novel, small software repository and a complete behavioural change request.
> Score the final patch in a clean container against a sealed conformance,
> regression, robustness, and performance suite.

This is one task contract with many generated, sealed instances. One fixed
repository would measure familiarity, memorisation, and luck rather than joint
capability.

## Methodology

The design combines:

- Gyre's separation of measurement, policy, and outcome;
- the reciprocal human-system controller;
- the prospective signal and constrained value layer;
- observer-tax, fixed-weak baseline, negative-control, and
  future-observation lessons;
- benchmark practices from software and research engineering.

SWE-bench's basic task shape is useful: a repository and issue are evaluated
with both fail-to-pass tests and pass-to-pass regression tests. Its verification
work also demonstrates the central fairness problem. In the original sample
audit, many issues were underspecified or paired with tests that could reject
reasonable solutions; SWE-bench Verified retained 500 samples only after three
annotators screened each one conservatively
([OpenAI, 2024](https://openai.com/index/introducing-swe-bench-verified/)).

Terminal-Bench contributes the containerised task, reference solution, and
comprehensive-test pattern
([Merrill et al., 2026](https://arxiv.org/abs/2601.11868)).
RE-Bench contributes direct human baselines, equivalent task conditions,
progressive scores with room below the ceiling, and resource-aware comparison
([Wijk et al., 2024](https://arxiv.org/abs/2411.15114)).
MLE-bench shows the value of an external held-out competition score, but its
data, compute, and expertise requirements are too high for Gyre's first
beginner-to-expert playground
([Shern et al., 2024](https://openai.com/index/mle-bench/)).

## Results

### 1. The task

Each attempt receives:

- a new repository instance generated after the controller version is frozen;
- a complete, plain-language behavioural contract;
- a small dependency-free or low-dependency Python package;
- visible examples and smoke tests;
- a broken implementation containing several interacting defects;
- a bounded terminal environment;
- a final submission command.

The first reference environment should be an **event-reconciliation package**.
The entrant must repair validation, ordering, deduplication, checkpoint/replay,
and summary behaviour. These requirements admit many correct implementations
but support an exact reference model, generated cases, invariants, and
metamorphic tests.

This task is suitable because:

- a beginner can inspect examples, run tests, and make a partial improvement;
- an experienced developer can reason about state, invariants, and failure
  recovery;
- an AI system can search, implement, test, and explain;
- a human-system team can decide how to divide diagnosis, implementation,
  verification, and strategy;
- loop quality matters because feedback, time, and probe opportunities are
  limited;
- the external outcome remains software behaviour, not a judge's opinion about
  whether the collaboration looked good.

The package domain is incidental. It must not contain Gyre-specific sensor or
controller concepts in the scored requirements, because that would build the
project's preferred method into the target.

### 2. The external outcome score

The **Verified Outcome Score** is a 0-100 score:

| Requirement family | Points | Evidence |
|---|---:|---|
| Declared behavioural conformance | 55 | Sealed generated examples checked against an executable reference model |
| Regression preservation | 15 | Existing unrelated behaviour remains unchanged |
| Robustness and metamorphic properties | 15 | Input transformations preserve declared invariants |
| Recovery, replay, and idempotency | 10 | Fault-injection and repeated-execution cases |
| Performance boundary | 5 | Deterministic instruction, time, or memory budget after correctness gates |

Weights are public and attached to requirement families. Individual hidden test
counts do not determine importance.

The score is:

\[
S = \sum_{k=1}^{5} w_k
\frac{\text{requirement cases passed in family }k}
     {\text{valid cases in family }k}
\]

Report the mean and interval across multiple hidden generator seeds. A single
lucky seed is not the leaderboard result.

Apply an integrity gate before scoring:

- the evaluator and tests remain read-only;
- the task container has no unrestricted network access;
- only declared source and configuration files may change;
- the patch must apply in a fresh container;
- no process may introspect hidden tests or evaluator secrets.

An integrity failure is a disqualification, not a utility penalty.

### 3. Why the score can be considered fair

The scoring instrument must qualify before it evaluates a controller.

For every task version:

1. Build an executable reference model independently of the starter
   implementation.
2. Trace every scored requirement to explicit text in the task contract.
3. Generate multiple structurally different correct implementations and check
   that the suite accepts them.
4. Generate adversarial incorrect implementations and check that the suite
   rejects them.
5. Run mutation testing against the evaluator to find unmeasured behaviour.
6. Have at least three independent reviewers assess underspecification,
   false-rejection risk, loopholes, and environment reliability.
7. Reject the task if any reviewer identifies a material hidden requirement.
8. Run the reference solution, alternate solutions, and intentionally invalid
   solutions in the same clean container used for submissions.
9. Freeze the task contract, category weights, scorer, container digest,
   generator, and analysis before generating final seeds.
10. Preserve every failed scorer-qualification receipt.

Public visible tests are teaching instruments, not the final criterion. Final
scoring uses untouched seeds and a separate evaluator path so entrants cannot
merely optimise to a disclosed fixture.

### 4. The observer tax makes loop design testable

Every team receives:

- unlimited local smoke-test runs;
- at most three **validation probes** against a visible-development seed bank;
- one final evaluation against untouched seeds.

A validation probe returns category-level scores and confidence intervals, not
hidden examples. It consumes time and one probe from the budget.

This creates a real control problem:

- Which uncertainty is worth probing?
- Should the team implement, inspect, test, reframe, or ask the human?
- When should it stop exploring and submit?
- Does a probe improve the decision enough to justify its cost and overfitting
  risk?

The final holdout remains unaffected by probing, so the outcome instrument is
not itself disturbed. The **development evidence state** is altered: every
probe consumes future optionality and can anchor the team on the development
distribution. This is a bounded observer tax on the development evidence state.

### 5. The joint-capability proxy

Raw team score is not evidence of complementarity. A team may simply contain a
strong system.

For the same human, system, task family, and version, estimate:

- \(S_H\): human-only outcome score;
- \(S_A\): system-only outcome score;
- \(S_{HA}\): human-system outcome score.

The primary joint-capability gain is:

\[
JCG = S_{HA} - \max(S_H,S_A)
\]

Positive `JCG` means the team outperformed its better constituent on that task
distribution. Report a paired interval across sealed instances. Do not call one
positive attempt joint-capability evidence.

Run four conditions:

1. human only;
2. system only;
3. human plus system with an ordinary chat interface;
4. human plus system with declared measurements, controllers, action menus, and
   prospective-value receipts.

Condition 3 is necessary. It separates the value of having both parties from
the value of the engineered loop.

### 6. Budgets and leaderboards

Human minutes, wall time, model tokens, API cost, and validation probes are not
naturally commensurable. Do not hide them inside one conversion rate.

Use three leaderboards:

1. **Outcome:** highest Verified Outcome Score under a generous fixed wall-time
   ceiling.
2. **Joint gain:** highest paired `JCG` under the preregistered experimental
   protocol.
3. **Efficiency frontier:** non-dominated combinations of outcome score, active
   human minutes, API cost, wall time, and probe count.

Create novice, standard, and open divisions:

| Division | Human time | System/API allowance | Purpose |
|---|---:|---:|---|
| Novice | 30 active minutes | modest fixed allowance | Accessible learning and partial progress |
| Standard | 60 active minutes | fixed published allowance | Comparable leaderboard |
| Open | reported, not capped except safety | reported | Explore the score ceiling |

The scientific joint-capability experiment uses only the Standard division.
The Open division is a playground, not clean causal evidence.

### 7. What every loop must log

The harness records:

- observations and sensor provenance;
- prospective human and system forecasts, locked before disclosure;
- controller recommendations and alternatives;
- human control-menu actions;
- terminal and validation-probe calls;
- checkpoints and recovery actions;
- human interruptions;
- final patch hash;
- objective and acceptance outcomes separately;
- tokens, API cost, wall time, active human time, and probe count.

Private reasoning content is not required. The trace needs typed control events,
not hidden chain of thought.

Entrants may submit:

- only a final patch for the outcome leaderboard;
- an event-compatible controller for loop analysis;
- a private hosted sensor or controller that exposes only the public contract.

### 8. Prospective signals the challenge can qualify

Before final evaluation, human and system controllers can forecast:

- probability of each score band;
- probability each requirement family passes;
- expected value of one more validation probe;
- expected recovery value of another revision;
- probability the current verifier is misleading;
- expected outcome of submit, inspect, test, reframe, or ask-human actions.

After the score is revealed, the harness can measure:

- Brier or log score;
- calibration and resolution by requirement family;
- incremental value of human and system signals;
- error dependence;
- whether probe-value predictions were correct;
- whether the selected actions reduced decision regret.

This is how the external outcome turns subjective control traces into testable
measurement and policy claims.

## Discussion

The Sealed Repository Rescue is the best first task because it balances four
requirements that pull in different directions:

- objective executable scoring;
- ecological software work;
- a low floor for newcomers;
- a high enough ceiling for sophisticated loops and controllers.

It should borrow benchmark formats, not reuse a saturated public benchmark as
the final leaderboard. Existing SWE-bench tasks risk memorisation and
contamination. Terminal-Bench tasks vary too widely for a clean first
human-system comparison. MLE-bench and RE-Bench are expensive and specialist.
A novel post-freeze task generator gives Gyre a fairer test while remaining
compatible with containerised benchmark harnesses.

The benchmark still measures a bounded construct: collaborative repository
repair under terminal access. It is a proxy for joint capability, not general
joint intelligence. Transfer requires a later, different task family.

## Next Steps

1. Write the behavioural contract and reference model for the
   event-reconciliation task.
2. Build the scorer before building any preferred controller.
3. Qualify the scorer with alternate-correct, adversarial-invalid, mutation, and
   three-reviewer fairness tests.
4. Run a cheap no-controller pilot to establish floor, ceiling, environment
   reliability, and score variance.
5. Freeze the Standard-division budgets and human/system comparison protocol.
6. Run human-only and system-only baselines before evaluating a joint loop.
7. Add the ordinary-chat joint condition before the measured-control condition.
8. Keep final generator seeds sealed until all controller settings and analyses
   are frozen.
9. Publish outcome, joint-gain, and efficiency-frontier receipts even if the
   measured-control condition loses.

## Public and protected boundary

Ship publicly:

- task and event contracts;
- visible examples and smoke tests;
- score categories and weights;
- container and evaluation client;
- scorer-qualification protocol;
- synthetic generator after final evaluation;
- baseline controllers and failed receipts.

Keep protected:

- active final seeds and hidden cases;
- evaluator secrets and anti-tamper rules that would enable evasion;
- fitted human/system fusion weights;
- private capability profiles and traces;
- proprietary sensors and production controller parameters.

Release retired hidden suites after each season. This makes old scores
reproducible without making the live evaluator gameable.
