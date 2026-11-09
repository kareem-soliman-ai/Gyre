# Engineering agent loops and graphs

> For the compact synthesis, start with [Gyre's Major Lessons](LESSONS.md).
> This document is the deeper design and evidence record.

Loop engineering and graph engineering are not competing disciplines. A loop is
a directed cycle. A graph is a set of operations, state, and transitions that may
contain many cycles. The useful question is not which label wins. It is:

> Where should judgement live, what evidence changes the route, and how will we
> know whether the added structure helped?

This guide turns Gyre's loop lessons into a framework-agnostic design method for
developers. It also states the evidence boundary: the method and the proving
ground are public; fitted, qualified instruments can remain behind the existing
measurement interface.

## What the current wave gets right

The July 2026 graph-engineering discussion names a real engineering object even
if the name is new. LangChain describes a graph as nodes that do work, edges that
choose what happens next, and state that moves between them. Its production
lessons are that agent graphs usually contain cycles, dynamic transitions matter,
and nodes now range from deterministic code to complete agent runs. It also
states a limit that matters: open-ended, path-dependent work can be made worse by
forcing it through a rigid graph
([LangChain, 2026](https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph)).

The frameworks broadly agree on the substrate:

- LangGraph exposes state, nodes, edges, persistence, interrupts, and resumable
  execution
  ([LangGraph guide](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph)).
- AutoGen's GraphFlow supports sequential, parallel, conditional, and looping
  execution, and explicitly calls for safe exit conditions
  ([AutoGen GraphFlow](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/graph-flow.html)).
- OpenAI's Agents SDK distinguishes manager-controlled specialists from
  handoffs where a specialist takes control, and supports typed handoff metadata
  and input filtering
  ([OpenAI agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/),
  [handoffs](https://openai.github.io/openai-agents-python/handoffs/)).
- Anthropic's production research system uses an orchestrator-worker graph, but
  reports that the architecture is most useful for valuable, highly parallel
  work and expensive elsewhere. Its internal system used about 15 times the
  tokens of chat interactions, so its result is evidence for selective use, not
  a universal multi-agent advantage
  ([Anthropic, 2025](https://www.anthropic.com/engineering/multi-agent-research-system)).

The graph itself is therefore not the missing abstraction. The harder questions
sit inside its edges: which observations are trusted, which coordination
mechanism fits the work, who has authority, and when a cycle should stop or
change.

## Prior art: agent graphs have always been organisations

Organisational design is not a new metaphor pasted onto agent graphs. It is part
of the multi-agent-systems lineage.

Van Aart, Wielinga, and Schreiber explicitly used Mintzberg's machine
bureaucracy, professional bureaucracy, and adhocracy as building blocks for
distributed intelligent systems. Their framework decomposed work into jobs and
then reintegrated those jobs through allocation and coordination mechanisms
([van Aart et al., 2004](https://www.cs.vu.nl/~guus/papers/Aart04a.pdf)).

Carley, Prietula, and Lin showed that agent capability and organisational design
interact: structure can substitute for some cognition, and cognition can mitigate
some structural limits. Their evidence spans simulation, experiments, and
archival organisational data
([Carley et al., 1998](https://www.jasss.org/1/3/4.html)).

Dignum and Dignum formalised reorganisation as an object with its own cost and
performance consequences rather than a free transition between structures
([Dignum & Dignum, 2006](https://webdoc.sub.gwdg.de/ebook/serien/ah/UU-CS/2006-060.pdf)).

The defensible Gyre contribution is therefore not "graphs are organisations".
It is a practical synthesis:

1. treat cycles as observable controllers;
2. treat conditional edges as measurement claims;
3. allocate coordination and authority from capability and consequence;
4. evaluate sensors, policies, and outcomes separately;
5. keep adaptive topology in shadow mode until it beats a fixed baseline.

## The design object

A useful loop or graph specification is larger than a prompt:

```text
task environment
  + state and reset boundary
  + nodes and capability evidence
  + edges and coordination contracts
  + sensors and their validity limits
  + policies and action authority
  + budgets and terminal states
  + persistence and recovery
  + human approval
  + evaluation and promotion gates
```

If one of those terms is missing, the implementation may still run, but its
failure will be hard to attribute.

## Lesson 1: start with the smallest topology that can work

The first design decision is not which graph framework to use. It is whether the
task needs a graph.

Use a deterministic function when the transformation is known and testable. Use
one model call when the task is a bounded judgement or generation. Use one agent
with tools when the path is open but the role, authority, and context are shared.
Add a loop when the work requires repeated observation and correction. Add a
graph when there are genuinely different operations, authorities, contexts, or
parallel workstreams.

This is not minimalism as taste. Coordination costs grow with every additional
node and edge. Anthropic's production report found multi-agent value mainly in
breadth-first, parallel research and explicitly warned about dependent tasks and
token cost. A graph earns its place by beating the simpler route on the same task
and budget.

## Lesson 2: an edge is a coordination mechanism

An arrow labelled "next" hides the most consequential part of a graph. State what
travels across it and why this mechanism fits.

| Mechanism | Use it when | Failure to test |
|---|---|---|
| Typed packet | Producer and consumer have a clear dependency | Schema drift, missing provenance, lossy handoff |
| Shared state | Several nodes need evolving common evidence | Stale reads, contamination, silent overwrite |
| Pipeline | A stable transformation has known stages | Upstream error amplification |
| Fan-out/fan-in | Search or generation can be independent | Duplicate work disguised as diversity |
| Manager-worker | One node must retain final authority | Manager context growth and bottlenecking |
| Handoff | A specialist should take control | Lost context, ambiguous ownership |
| Human interrupt | Consequence or judgement exceeds automation | Approval fatigue, missing resumability |

One useful implementation lesson from a sibling design system is that shared
state and typed packets are complementary. The packet log is the evidence
substrate; derived boards can be projections over it; unresolved tensions need
separate, append-only state. Re-copying prose between agents creates drift.
Referencing typed artefacts by stable identity preserves provenance and keeps
disagreements inspectable.

## Lesson 3: every conditional edge contains a sensor and a policy

Consider:

```python
if progress_is_low(state):
    goto("reframe")
```

That one edge contains two independent claims:

1. `progress_is_low` correctly measures a latent state;
2. `reframe` is the right action when that state is present.

Gyre calls the first part the sensor and the second the controller. They should be
replaceable and testable separately. A lexical-similarity rule, a model's
self-assessment, and a calibrated information-gain instrument can all feed the
same route, but they have different maturity and different confounds.

This yields a graph-level rule:

> A routing graph is only as trustworthy as the least valid instrument on a
> consequential path.

This is a Gyre synthesis, not yet a general empirical law. It is directly
testable: hold the graph and policy fixed, replace the routing sensor, and measure
the downstream decisions.

## Lesson 4: allocate control from capability and consequence

Capability alone does not determine autonomy. A highly capable node can still
take an irreversible action. A weak node can safely perform a cheap, reversible
check.

Use this design matrix:

| | Low consequence | High consequence |
|---|---|---|
| Low demonstrated capability | Deterministic constraint and tight checks | Do not automate the action |
| High demonstrated capability | Broad autonomy within a budget | Corrective feedback plus human approval for the irreversible step |

This produces two different loop shapes:

- A **cage** constrains a low-capability component before or during action.
- A **mirror** returns discrepancy evidence to a capable component and lets it
  correct within its authority.

The cage/mirror distinction is a design hypothesis derived from Requisite
Coordination, not a validated performance claim. It earns its place by producing
falsifiable choices: compare strict process control with output-standardised
feedback at matched capability, consequence, and budget.

Human attention goes where consequence is high and automated verification is
weak. A meta-controller that changes authorities or topology is itself a
high-consequence node, so it requires a permanent human approval boundary for
material changes.

Capability evidence is decision-local and longitudinal, not one global score.
Before asking the human, classify missing facts by who can supply them:

| Missing fact | Default resolution |
|---|---|
| Human intent, taste, authority, or consequence tolerance | Ask once upfront if the answer changes the route |
| Repository state, tests, source versions, or verifier health | Inspect through autonomous preflight |
| Evidence neither party currently has | Seek evidence or use a conservative default |

This matters for interruption policy. A failed check can stop an action without
stopping the human. When the system can diagnose and restore independent
verification inside a bounded recovery budget, it should do so autonomously and
teach through its receipt. Interrupt the human only when recovery is exhausted,
authority must change, consequences become high, or unresolved judgement needs
the human's stronger capability.

### The human is also a sensor and controller

Do not draw the human as a terminal accept-or-reject node. Their observation is
a scoped measurement with a target, cues, confidence, error, confounds, and
capability boundary. Their decision is a control transition.

When a human decision is required, expose a real action menu:

- follow the recommendation or choose a surfaced alternative;
- request evidence;
- revise the success criterion;
- change the authority boundary;
- delegate a bounded action with a verifier and budget;
- pause the action while preserving the goal;
- terminate the whole goal.

State the consequence, next state, reversibility, and evidence effect of each
option. Human uptake is not objective quality evidence. When no decision is
required, keep controls available without generating an interruption.

The same maturity ladder can be applied to human observation: raw, standardised,
calibrated, and self-deciding within a bounded task family. Calibration requires
prospective predictions and later outcomes. Expertise outside the evidenced
task family should not transfer by assumption. See
[first-principles-loop-control.md](first-principles-loop-control.md) for the
psychological evidence and [the Loop Control Lab](loop-control-playground.md)
for executable cases.

## Lesson 5: prompts define roles inside the control system

The production lesson from Anthropic is that effective multi-agent prompts define
objectives, output formats, tool guidance, task boundaries, and effort budgets.
That prevents duplicate work and runaway delegation. Gyre adds a separation that
prompting practice often misses: do not fuse generation, sensing, and control
into one vague instruction.

Use three contracts:

**Generator**

```text
Perform the object-level task. Report what changed, what evidence arrived, and
which acceptance criterion the change addresses.
```

**Sensor**

```text
Compare the latest step with the recorded attempts. Cite the trace item that
contains genuinely new evidence. If none exists, report no_information_gain.
Name uncertainty and likely confounds. Do not choose the next action.
```

**Controller**

```text
Choose one declared action using the sensor report, remaining budget, and action
authority: continue, reframe, seek_info, switch, escalate, or stop. Record the
reason and the terminal state when stopping.
```

This can still run on one model, but the roles remain inspectable. A model judging
its own trace in the same context is a correlated self-report. Metacognitive
co-regulation evidence supports taking the distinction seriously: in one 2026
engineering-design task, a separate co-regulation agent outperformed
self-regulation, while the self-regulation loop did not significantly beat the
plain loop on the headline comparison
([Xu et al., 2026](https://arxiv.org/abs/2603.24768)). That is one task and should
not be universalised, but it is a strong reason to test external regulation rather
than assume self-critique is independent.

## Lesson 6: prompts cannot validate their own sensors

"Check whether you are stuck" may be a useful intervention. It is also a sensor
with unknown sensitivity and specificity.

Calibration requires comparison with a criterion the prompt did not generate. A
more articulate self-assessment is not calibration. For low-cost failures, use
the cheap prompt and log its calls. For expensive or silent failures, run it in
shadow mode and collect paired evidence before allowing it to route.

Structural attacks reinforce this boundary. Recent work induced expensive agent
cycles through plausible tool-call sequences and found that token-level concision
controls did not reliably prevent them; the defence has to inspect tool-call
structure, not only generated prose
([Lee et al., 2026](https://arxiv.org/abs/2602.14798)).

## Lesson 7: dynamic topology is a controller, not free intelligence

A runtime system may want to change its fan-out, roles, or routes as the task
changes. That is a meta-loop. It needs:

- a regime sensor;
- a switching decision;
- a switching-cost model;
- hysteresis or a hold period;
- rollback and state migration;
- a fixed baseline;
- a promotion gate.

Default to fixed topology. Log adaptive recommendations in shadow mode without
acting on them. Promote only after the adaptive system beats the fixed system
under a matched budget and the advantage survives the cost of changing the
topology. Otherwise the apparent intelligence is churn.

## Lesson 8: evaluate the chain, not one blended score

Use three links:

| Link | Question | Hold fixed |
|---|---|---|
| A: sensor | Does the signal detect the intended loop or graph state? | Policy and task |
| B: policy | Given a known signal, does the route choose a useful action? | Sensor |
| C: outcome | Does the whole system improve quality, cost, latency, or risk? | Budget and baseline |

Add trap cases:

- healthy repetition that should not be stopped;
- an unsolvable task where no policy can create success;
- a corrupted sensor;
- a capable node under excessive constraint;
- a weak node given too much discretion;
- a topology switch whose transition cost erases its benefit.

A pooled win that fails a trap cell is measuring the wrong thing.

## Lesson 9: a measurement node may also be an action node

Do not assume an observation is a read-only edge. Testing, asking, scanning,
explaining, or verifying can alter:

- the object being measured;
- the mechanism through which later actions work;
- the evaluator or instrument;
- a human's attention, confidence, or behaviour; or
- the availability and quality of future evidence.

Model those effects as causal edges and keep immutable phenomenon IDs separate
from participant-created aliases. Names and explanations are hypotheses; score
their predictions and downstream control value rather than vocabulary match.

The [Alien Factory expedition](observer-effects-challenge.md) makes this
runnable with active and reference instruments, variable naming, an action
budget, and objective terminal scoring.

## The public playground and the proprietary fence

Gyre can make the method runnable without publishing the part that took
measurement research to earn.

| Public in this repository | Protected behind the seam |
|---|---|
| Loop taxonomy and graph design method | Fitted instrument parameters |
| `MeasurementProvider`, `Measurement`, and controller interfaces | Private labelled corpora |
| Naive sensors and fixed controllers | Corrected feature machinery |
| Synthetic generators, trace formats, and trap cells | Validated operating points |
| Benchmark and challenge harness | Proprietary adaptive-controller policies |
| `loop-engineer` skill, JSON template, and validator | Hosted analytics and private user-trace comparisons |
| Joint-control compiler, public contracts, and qualification harnesses | Fitted user capability profiles, private calibration histories, and learned thresholds |
| Shadow-mode recommendations and promotion protocol | Calibration updates learned from private data |

The hosted boundary returns the same public `Measurement` shape: value, meaning,
calibration fields where earned, measurement error, confounds, provider identity,
and relevant detail. It does not need to return weights, thresholds, training
data, or feature implementations.

This creates a credible playground:

1. A developer designs a loop or graph with
   [`skills/loop-engineer`](../skills/loop-engineer/SKILL.md).
2. For long-horizon collaboration, the developer compiles a decision-local
   contract with
   [`skills/compile-joint-control`](../skills/compile-joint-control/SKILL.md).
3. The JSON contracts pass their public validators.
4. The developer runs a naive public sensor in shadow mode.
5. The benchmark exposes where the proxy fails.
6. A hosted instrument can be swapped in without changing the graph.
7. The outcome comparison demonstrates value through behaviour, not secrecy or
   assertion.

## A compact review checklist

Before writing framework code, answer:

- What is the simpler baseline?
- Why does each node need distinct context, capability, authority, or parallelism?
- What typed state crosses each edge?
- Which conditional edges depend on latent constructs?
- What is each sensor's maturity and largest confound?
- Can observing or verifying change the object, mechanism, evaluator, human, or
  future evidence?
- If latent variables are unnamed, are immutable IDs separate from revisable
  participant aliases?
- Are generator, sensor, and controller responsibilities separate?
- What are the named terminal states and hard budgets?
- Where is the human approval boundary?
- Which unknowns should the system preflight instead of asking the human?
- Can a failed check recover autonomously before it interrupts the user?
- What is checkpointed, and when is state reset?
- Is adaptive topology fixed, shadow, or active?
- What switching cost and hysteresis prevent thrashing?
- How will Links A, B, and C be evaluated independently?

If these answers are absent, a framework can make the graph executable, but it
cannot make the design defensible.

## What is evidence and what remains a programme

**Observed in sources and live code:** current agent frameworks expose graphs as
state, nodes, edges, cycles, persistence, and human interrupts; production
multi-agent systems require bounded delegation, budgets, observability, and
resumability; historical MAS research already imports organisational design; a
sibling design system implements typed packets, a shared ledger, deterministic
gates, a fixed topology, and a non-acting Gyre shadow monitor.

**Gyre synthesis:** conditional edges should be treated as measurement
instruments; the graph inherits the validity limits of consequential routing
sensors; capability and consequence should jointly determine loop type and human
attention.

**Not yet proved:** that the cage/mirror allocation improves outcomes across
tasks, that adaptive topology beats fixed topology after switching costs, that
Gyre's current public sensors transfer from synthetic cells to real agent traces,
or that the developer skill improves implemented systems. Those are evaluation
targets, not launch claims.

The controlled qualifications sharpen that boundary. EXP-01 and EXP-02 did
not qualify `loop-engineer`; v1.1 reached 11/16 executable contracts versus 9/16
for its template but missed the marginal gate. The current v1.2 observer-effect
revision has not been evaluated. EXP-03's intake criterion was
invalid and is retained as a failed measurement receipt. EXP-04's
Joint Capability Compiler improved conditional final contracts to 10/16 versus
5/16 for its template with zero unsafe routes, but its joint gate remained at
floor because the experiment and skill still confused technical preflight with
human questions. EXP-05A passed only its scorer engineering sub-gate; EXP-05B
hit a task ceiling. EXP-06 qualified synthetic observer-effect mechanics and
generous-budget discoverability, not the budgeted expedition or external
transfer. See the [experiment index](../experiments/INDEX.md). None of these
studies establishes real joint capability.
