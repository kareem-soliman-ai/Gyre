---
name: loop-engineer
description: "Designs and audits bounded agent loops and agent graphs as observable control systems. Use when a developer asks to build an agent loop, stop an agent repeating itself, turn a workflow into a graph, add routing or handoffs, choose between one agent and multiple agents, add reflection or critique, define exit conditions, govern dynamic topology, or improve an agent prompt that says keep trying. Also triggers when a loop or graph needs budgets, checkpoints, human escalation, measurement, shadow mode, or a matched baseline. Prefer this over framework-specific coding guidance when the unresolved problem is the control design; use framework documentation after the design contract is valid."
license: Apache-2.0
metadata:
  author: kareem-soliman
  version: "1.2.0"
---

<!-- STRUCTURAL DECLARATION
Configuration: Simple Structure for design judgement plus one deterministic
validation gate.
Coordination: Sequential. One agent can do this work; extra agents would add
coordination cost without an independent verification benefit.
Freedom: HIGH for construct and topology diagnosis, MEDIUM for contracts and
prompts, LOW for manifest validation.
Evidence boundary: Gyre supplies design hypotheses, public baselines, and
falsification machinery. It does not turn an unvalidated signal into an
instrument by describing it confidently.
-->

# Loop Engineer

As the engineer responsible for an agent's control structure, make every cycle
and transition answerable: what state is being controlled, what evidence changes
the route, who is allowed to act, how the run ends, and how anyone could tell
whether the added structure beat a simpler system.

Four constraints survive every design:

1. A loop is a controller, not a prompt that says "keep trying". Name its sensor,
   decision rule, action menu, terminal states, budget, and persistence boundary.
2. A conditional edge is a measurement claim. Separate the signal from the policy
   that acts on it and state the signal's maturity and confounds.
3. Graph complexity earns promotion against a fixed, simpler baseline. Dynamic
   routing starts in shadow mode and carries switching cost and hysteresis.
4. Observation may be an intervention. Record what a probe can change, compare
   a no-probe or renewable negative control, and price future evidence as well
   as immediate information.

Read [the Gyre loop-and-graph guide](../../docs/loop-and-graph-engineering.md)
when the design involves multiple nodes, human approval, or adaptive topology.

## Phase 1: Diagnose before drawing

Start with the task, not a favourite framework.

1. State the objective, failure cost, reversibility, and evidence of completion.
2. Copy every hard task limit into a `task_constraints` entry with the
   requirement, where it is enforced, and the failure state. Numeric limits
   mentioned only in prose are not controls.
3. Name the simplest credible baseline: deterministic function, one model call,
   one agent with tools, or one fixed loop.
4. Add a loop only when the task needs repeated observation and correction.
5. Add a graph only when there are genuinely different operations, authorities,
   contexts, or parallel workstreams.
6. If the work is open-ended and path-dependent, keep judgement inside a capable
   node instead of hard-coding a brittle maze of edges.

Select one initial topology: `single-call`, `single-loop`, `pipeline`,
`fan-out/fan-in`, `manager-workers`, `handoff`, or `state-graph`. Explain why the
simpler baseline is insufficient without claiming that the selected topology is
already better.

## Phase 2: Specify the graph as a mini-organisation

Classify each node as `deterministic`, `model`, `agent`, or `human`. For every
node record:

- one purpose and typed inputs/outputs;
- capability evidence, not persona confidence;
- action consequence (`low`, `medium`, or `high`);
- authority and forbidden side effects;
- failure policy, checkpoint, and recovery route.

High-consequence actions retain human approval even when the node is capable.
This prevents the common rationalisation that a strong model makes consequence
irrelevant. Classify the consequence of the action the node can actually take,
not the seriousness of the surrounding domain: drafting a patch can be
reversible, while deploying it is high consequence. If a node is labelled
`high`, `human_approval` must be `true`.

Treat edges as coordination mechanisms, not arrows. Choose deliberately among:

- typed packet for a clear producer-consumer dependency;
- shared state for many readers of evolving evidence;
- pipeline for stable transformations;
- fan-out/fan-in for independent search or generation;
- handoff when the receiving specialist should take control;
- human interrupt for consequential approval or missing judgement.

For each edge record its guard, handoff contract, failure path, and provenance.
Represent disagreements as state or typed tensions; silent overwrite destroys the
evidence needed to debug the graph.

## Phase 3: Specify every cycle as a control loop

For each directed cycle, fill these slots:

| Slot | Required question |
|---|---|
| Controlled variable | What should move or remain bounded? |
| Observation | What trace event is actually visible? |
| Sensor | How is the latent state inferred from that event? |
| Maturity | Raw proxy, standardized, calibrated, or self-deciding? |
| Confounds | When will the signal fire for the wrong reason or miss the state? |
| Observer effect | Can observing change the object, mechanism, evaluator, human, or later evidence? |
| Decision rule | What evidence changes the route? |
| Action menu | Continue, reframe, seek information, switch, escalate, stop? |
| Terminal states | What named outcomes end the run? |
| Budget | Maximum cycles, cost, time, and tool calls? |
| Persistence | What checkpoint survives interruption, and when is state reset? |

Use external deterministic signals where they fit. If the generator judges its
own trace in the same context, label that channel `same_context`: it is a cheap
self-report with correlated blind spots, not independent measurement.

Treat a measurement as causally quiet only when the environment or an explicit
negative-control comparison supports that assumption. Otherwise record the
possible affected state, expected disturbance, intensity, reversibility, and
future-observation cost. More verification is not automatically safer.

When a loop is discovering unknown latent variables, keep immutable machine IDs
separate from participant-created names and explanations. Names are revisable
hypotheses. Evaluate them through prospective predictions and outcomes, not by
matching the designer's vocabulary.

Default a new sensor to `raw`. Use `calibrated` only when the spec cites a
calibration receipt, dataset, and criterion under `calibration_evidence`.
Confident wording or a planned evaluation does not earn a maturity label.

Give the controller a menu rather than a binary retry/stop switch. A plateau can
call for new evidence, a reframe, a different specialist, a human, or a clean
abandon-with-note. Repeating the same action under paraphrased instructions is not
adaptation.

## Phase 4: Write three prompt contracts

Produce separate prompt blocks even if one runtime model executes all three:

- **Generator:** performs the object-level work and reports what changed.
- **Sensor:** extracts observable evidence and names uncertainty; it does not
  choose the next action.
- **Controller:** chooses only from the declared action menu using the sensor
  report, authority limits, and remaining budget.

Store all three inside `loop-graph-spec.json` under `prompt_contracts`. They may
also be rendered as separate blocks for a human reader, but the
machine-checkable copy is canonical.

Prompt the discriminator, not the symptom. Prefer:

> State the new evidence produced by the last step relative to the recorded
> attempts. Cite the trace item. If no new evidence arrived, report
> `no_information_gain`.

over:

> Check whether you are looping and keep improving until done.

The first prompt still needs validation. Better wording does not calibrate the
sensor that wording creates.

## Phase 5: Gate adaptation and evaluate the chain

Default to a fixed topology. A proposed adaptive route runs in `shadow` mode:
record what it would have changed without changing control flow.

Promotion to `active` requires:

1. a matched-budget comparison with the fixed baseline;
2. Link A evidence that the sensor agrees with an independent criterion;
3. Link B evidence that the policy routes well with the sensor held fixed;
4. Link C evidence that the whole system improves task outcome, cost, or risk;
5. explicit switching costs and hysteresis so noisy readings cannot thrash the
   topology;
6. trap cases including healthy repetition, an unsolvable task, and a corrupted
   or misleading sensor.

Synthetic evidence can qualify machinery and expose confounds. It does not prove
transfer to real traces.

## Deliverable

Create:

1. `loop-graph-spec.json`, following
   [assets/loop-graph-spec.json](assets/loop-graph-spec.json), including
   `task_constraints` and `prompt_contracts`;
2. a human-readable note of at most 120 words explaining the baseline, selected
   topology, largest measurement risk, and promotion gate.

Keep the package compact. Do not repeat the task brief in every node, edge, risk,
and prompt. Prefer one concrete sentence per field and remove any node that lacks
a distinct operation, authority, context, or parallel workload.

Run:

```bash
python scripts/validate_spec.py path/to/loop-graph-spec.json
```

Fix every `FAIL`. Review each `WARN` explicitly. A passing manifest proves
contract completeness, not empirical value.

Maintainers should rerun the cases in
[references/evaluation-cases.md](references/evaluation-cases.md) after changing
the skill. The current record is a structural walkthrough because this build
surface did not permit a clean-context behavioural run.

## Premortem: how this design usually dies

- **Decorative sensing:** the prompt says "reflect" but no observable evidence can
  change the route. Cure it by naming the observation and decision rule.
- **Graph theatre:** extra agents restate one another while cost rises. Cure it by
  restoring the simpler baseline and requiring distinct authority, context, or
  parallel work for each node.
- **Adaptive thrashing:** runtime routing changes on noisy state with no cost of
  change. Cure it with shadow mode, hysteresis, and a matched-budget promotion
  gate.
- **Judge-judged collapse:** the generator's confident self-assessment is treated
  as ground truth. Cure it with an external channel and independent labels where
  consequence warrants them.
- **Risk-note absolution:** the design admits that a high-consequence path lacks
  approval and ships anyway. A risk entry does not repair an invalid contract;
  change the authority or lower the action's actual consequence before shipping.

## What this skill does not do

- It does not select a framework or write framework-specific APIs before the
  control contract is coherent.
- It does not claim a prompt, judge, or proxy is validated without external
  evidence.
- It does not expose Gyre's fitted instruments, private corpora, operating points,
  or proprietary adaptive controllers.
- It does not add multiple agents when one bounded agent plus deterministic checks
  is a credible baseline.

## Completion

Finish only when the manifest passes the validator, the three prompt roles remain
separate inside `prompt_contracts`, every hard task limit has an enforceable
`task_constraints` entry, every cycle has named terminal states and a budget,
every conditional edge names its signal and confounds, high-consequence actions
retain human approval, and any adaptive topology remains shadowed until its
promotion gate is evidenced. Do not treat listing a validator failure under
`risks` as completion. Report the largest unresolved validity risk and the next
cheapest test.
