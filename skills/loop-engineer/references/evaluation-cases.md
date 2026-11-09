# Evaluation cases

## Evidence status

The original cases below remain structural regression fixtures. EXP-01 added a
controlled behavioural comparison on three different, held-out briefs:
`experiments/EXP-01_LoopEngineerSkillQualification_2026-07-28/`.

EXP-01 did not pass its preregistered gate. Across 18 blind votes, 11 favoured
the skill, 4 favoured no skill, and 3 tied. The mean composite improved by
0.746, but the skill produced two unsafe-authority flags versus one and used
2.18 times the completion tokens. Version 1.1.0 addressed the observed
authority contradiction, unearned calibration label, prompt-location mismatch,
missing hard constraints, and output bloat. EXP-02 then evaluated v1.1.0:
the skill passed 11/16 executable contracts versus 9/16 for the template and
missed its preregistered absolute and marginal gates. Version 1.2.0 adds
reactive-measurement and latent-naming discipline and is unqualified.

## Case 1: vague coding loop

**Prompt**

> Make my coding agent keep fixing the implementation until all tests pass, but
> stop it wasting tokens when it gets stuck.

**Baseline gap**

The earlier skill names trigger, sensor, policy, budget, and escalation, but can
still allow "test pass rate" to act as both outcome and loop-state sensor. It does
not force separate generator, sensor, and controller prompts or an unsolvable-task
trap.

**This skill must add**

- a deterministic test runner as an external sensor;
- evidence gain for repeated failing cycles;
- named terminal states for passed, blocked, budget exhausted, and no information
  gain;
- an unsolvable-task trap and a last-good checkpoint;
- separate prompt contracts.

## Case 2: support workflow graph

**Prompt**

> Turn our support workflow into a graph with triage, billing, technical support,
> and manager approval for refunds.

**Baseline gap**

The single-loop contract does not require a simpler baseline, typed edge
contracts, state ownership, capability evidence, or consequence-based human
approval.

**This skill must add**

- a comparison with one triage agent using specialists as tools;
- typed handoffs and input filtering;
- a high-consequence refund node with human approval;
- routing-sensor maturity and confounds;
- persistence and reset boundaries.

## Case 3: adaptive research topology

**Prompt**

> Let a research agent decide at runtime how many subagents it needs and switch
> strategies when the search is not working.

**Baseline gap**

The earlier skill defaults to fixed control and asks for a promotion gate, but it
does not require the graph's switching costs, hysteresis, fixed-versus-adaptive
matched-budget comparison, or Link A/B/C attribution.

**This skill must add**

- fixed topology as the initial mode;
- shadow recommendations before active switching;
- fan-out cost and state-migration cost;
- hysteresis or a hold period;
- separate evaluation of regime sensor, switching policy, and research outcome.

## Trigger near-misses

These should not activate the skill:

- "Show me the Python syntax for a `for` loop."
- "Explain graph databases and Cypher."
- "Plot this network as a graph."
- "Write one system prompt for a customer-support chatbot."

Those are language syntax, graph data, visualisation, or ordinary prompt-writing
requests. This skill is for recurring agent control and coordination structures.
