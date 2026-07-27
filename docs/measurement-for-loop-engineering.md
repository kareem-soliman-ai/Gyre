# Your agent loop is only as good as the evidence it runs on

**A measurement-science account of loop engineering: why sensors, controllers and outcomes have to be separated, and how to run the experiment that tells you which one is broken.**

Audience: engineers building agentic systems. No psychology background assumed. Every unfamiliar idea is bridged to something you already use.

---

## 1. The situation: we ship control systems with no instruments

Open any agent framework and count the loops. Retry on failure. Reflect and revise. Plan, act, observe, replan. Generate then verify. Escalate after N attempts. Each of these is a **control loop**: something decides whether to keep going, change approach, or stop.

Now look at what those decisions are actually made from. Almost universally:

```python
for attempt in range(MAX_STEPS):        # a constant someone guessed
    result = act()
    if verified(result):
        break
    if attempt > PATIENCE:              # another guessed constant
        escalate()
```

`MAX_STEPS`. `PATIENCE`. Retry counters. Timeouts. These are **blind heuristics**: they count iterations rather than measuring whether the iterations are accomplishing anything. An agent that has solved the problem and an agent that has been rewriting the same broken function twelve different ways look identical to a step counter.

You already know this is wrong in every other part of your stack. You would not run a service on "restart it every 100 requests" instead of a health check. You would not evaluate a model on "it ran for 3 epochs" instead of a validation metric. But agent loops routinely ship exactly that way, because the health check for *"is this loop still learning anything?"* does not come in the box.

Building that health check is what loop engineering is. Making it trustworthy is what measurement science is. This document is about why the second part is harder than it looks, and how to do it in a way that survives contact with a sceptic.

---

## 2. The separation that makes everything else possible

The single most important architectural decision is this:

> **A loop is a controller. A measurement is a sensor. They must be separate components, connected by an interface, and neither should import the other.**

This is straight control theory, and it comes with control theory's central lesson: **a controller is only as good as its sensor.** A thermostat with a brilliant PID algorithm and a broken thermometer will heat your house to 40°C with perfect confidence. The sophistication of the decision rule cannot compensate for bad input.

Here is the same idea in a language most engineers find more immediate:

> **Evidence-based decision-making is only as good as the evidence it relies on.**

A decision procedure can be flawless and still produce disastrous decisions if the evidence feeding it is noisy, biased, or measuring the wrong thing. This is why medicine separates the diagnostic test from the treatment protocol, and why both are evaluated separately. Nobody says "this treatment protocol has 94% accuracy". The protocol and the test are different objects with different failure modes.

There is an important refinement, and it is worth stating carefully because the slogan overshoots:

**It is not true that only the sensor determines quality.** A bad controller can waste a perfectly good signal — terminating when it should reframe, or reframing when the next attempt would have succeeded. The precise claim is:

> Sensor quality and controller quality are **separable causal contributors** to outcomes. Therefore they must be **tested separately**. The architecture is what permits that test.

If your sensing logic is inlined in your control flow — an `if` statement comparing a similarity score to a magic number, buried inside the retry loop — you have fused two components with independent failure modes into one untestable blob. When outcomes are bad you cannot tell whether your evidence was wrong or your decision was wrong, and you have no way to improve either without guessing.

**Concretely, the seam looks like this.** The controller depends only on an interface:

```python
monitor = RuminationMonitor(provider, patience=3)   # any sensor satisfying the protocol
for attempt in agent_attempts:
    monitor.observe(attempt)
    if monitor.verdict().exit_reason is not ExitReason.CONTINUE:
        break                                        # plateau: reframe, seek info, escalate
```

Swap `provider` and the control flow does not change a line. That is what makes "does a better measurement produce better behaviour?" an *experiment* rather than an *assertion*.

---

## 3. What measurement science adds: an earned number, not a plausible one

Here is where most agent evaluation goes wrong, and it goes wrong in a way that is invisible from inside.

You want to detect when an agent is stuck in an unproductive loop. So you write something reasonable: compare consecutive outputs, and if they are too similar, the agent is looping. Ship it.

You have just built a **proxy** and started treating it as an **instrument**. The difference matters enormously.

### The construct problem

"This agent is stuck" is not a fact you can read off a trace. It is a **latent construct** — something real that you cannot observe directly and must infer from observable behaviour. Latent constructs are the native territory of psychometrics, which has spent a century on exactly this problem, and its first lesson is: *you must say what you are actually measuring, because it will not be what you assumed.*

Take the specific case. Productive iteration and unproductive iteration look nearly identical on the surface — both are an agent going round again. What separates them?

- Not **iteration count**. Five attempts might be diligent debugging or five identical retries.
- Not **surface similarity**. An agent can rename every variable and change nothing that matters; it can also make one character's difference that fixes everything.
- The actual discriminator is **information gain**: did this step introduce something new — new evidence, a narrowed hypothesis space, a genuine reframe — relative to what has already been tried?

That reframing is where the psychology earns its place. It is not "psychology says feedback loops are important". It is that psychology has already studied these loop structures in humans and, crucially, has already identified **discriminators** between their productive and pathological forms. Rumination versus reflection is a studied distinction with a known discriminator. That saves you from inventing one badly.

### Every proxy is confounded, and you must say how

Once you know what you are trying to measure, you can name what your proxy gets wrong:

| Proxy | What it rewards by mistake |
|---|---|
| Consecutive text diff | **Thrashing.** An agent that rewrites everything each pass scores maximally novel while getting nowhere. Also fooled by renaming. |
| Embedding distance | Can score a genuine reframe as noise, and paraphrase as progress. |
| Error entropy | Assumes the environment returns informative errors. Silent failure looks like stability. |
| Iteration count | Blind to content entirely. |

Publishing confounds is not modesty, it is the interface contract. A measurement that does not declare how it can be wrong cannot be used safely by anyone downstream.

### Reliability and validity are different, and you need both

- **Reliability** — does it give the same answer twice on the same input? A sensor that flips its verdict between identical runs is unusable regardless of accuracy.
- **Validity** — does it measure the construct it claims? A sensor can be perfectly reliable and consistently measure the wrong thing.

Engineers routinely check the first (rerun it, see if it's stable) and skip the second. Consistency feels like correctness. It isn't.

### A number without an operating point is not a decision

A sensor that returns `0.73` has not made a decision. Someone still has to supply the threshold — and that threshold is where most of the real difficulty lives, because the right value depends on the task, the cost asymmetry, and the domain.

This produces a **calibration ladder**, and where a sensor sits on it tells you how much guessing it is offloading onto you:

1. **Raw value only.** You must supply the threshold. You will get it wrong, because the right value depends on things the sensor does not know.
2. **Baseline-relative (z-score).** The sensor knows what normal looks like for *this* trace, so "unusual" is defined without a global constant.
3. **Calibrated probability.** The sensor is a classifier of the latent state and reports a probability you can threshold by cost.
4. **Self-deciding.** The sensor owns its decision boundary and reports a verdict plus its own estimated error.

An instrument that has climbed this ladder is doing work that a raw proxy silently pushes onto you. And note the trap: an operating point fitted in one domain **need not transfer** to another. A threshold tuned on curated examples can saturate — firing on everything — when pointed at production traffic with different base rates. You already know this pattern from any classifier deployed against a shifted distribution.

---

## 4. Three links in the chain, each of which can break independently

Here is the diagnostic frame that makes the whole discipline click. Think about a smoke detector.

- **Link A — detection.** Does it identify smoke when smoke is present, without sounding constantly at burnt toast?
- **Link B — action.** When it sounds, does anybody actually do the right thing?
- **Link C — outcome.** Did those actions reduce fire damage, at an acceptable false-alarm cost?

Now the agent version:

- **Link A — detection.** Does the sensor agree with a defensible criterion about whether this loop is recycling or progressing?
- **Link B — intervention.** When it fires, does the agent actually change behaviour — reframe, seek information, escalate, park the impasse — or just carry on?
- **Link C — outcome.** Do those interventions improve task success, cut wasted iterations and tokens, and cost less than the waste they prevent?

**A sensor can win Link A and lose Link C.** It might detect correctly but fire too late to matter, trigger an unhelpful intervention, interrupt a recovery that was about to work, or cost more to run than the waste it avoids.

If you have worked on recommender systems or search, you already know this shape precisely: **offline metric wins routinely fail to produce online lift.** Detection accuracy is an offline metric. Task success is the online metric. Nobody in ranking would accept "our NDCG went up" as proof that revenue went up, and nobody should accept "our rumination detection F1 went up" as proof that agents got better.

So the honest causal chain is:

```
sensor detects → controller routes → agent behaviour changes → task outcome changes
```

Four nodes, three arrows, and **every arrow can fail on its own.** The discipline is refusing to smuggle a win at one arrow into a claim about the whole chain.

### An objection worth working through

If the sensor has genuinely established that the current strategy is producing no new information, isn't stopping obviously correct? What is there left for the controller to get wrong?

The answer is that **"terminate this loop" is not "terminate this task."** A good controller has a menu:

- reframe the problem or change representation
- seek the missing information — a tool call, a test, docs, a human
- switch strategy or move to a different subtask
- escalate with a compact record of what has already been tried
- park the impasse so a future session does not silently repeat it

The point is never "stop working". It is: **stop paying for a strategy that has stopped learning, then route the effort somewhere that can still produce information.** A controller that responds to every plateau by killing the task has taken a correct signal and made a bad decision with it — and that is a *controller* failure, invisible to any amount of sensor evaluation.

Two further qualifications sharpen it:

1. **The sensor may be wrong or uncertain.** "No information gain" is itself an inference from a trace. This is why confidence, declared confounds and calibration are load-bearing rather than decorative.
2. **Local loop health is not the whole decision.** A correctly identified plateau still has to be weighed against stakes, remaining budget, switching cost, and the value of a possible recovery. If a test run is nearly finished, one more attempt is cheap. If every attempt burns expensive context, switching earlier dominates.

---

## 5. The experiment: telling a bad sensor from a bad controller from a hard task

This is the core of the discipline, and it is where most agent evaluation simply has no answer. A single leaderboard number cannot tell you which component to fix. A **factorial design** can.

### 5.1 The three factors

**Factor 1 — SIGNAL** (what reaches the controller):

| Level | Description |
|---|---|
| `blind` | No sensor. The controller runs on counters alone. |
| `naive` | A cheap, honest proxy (consecutive diff novelty). The floor a real instrument must beat. |
| `candidate` | The sensor under test. |
| `oracle` | Ground-truth labels injected directly as the signal. **Only available where you have labels** — this is the crucial condition and the reason synthetic data is not optional. |
| `corrupted(ε)` | The oracle signal, deliberately degraded at a known error rate ε. Lets you sweep evidence quality as a continuous variable. |

**Factor 2 — POLICY** (what the controller does with the signal):

| Level | Description |
|---|---|
| `none` | No intervention. Run to the cap. |
| `blind-heuristic` | Standard practice: retry N times, then escalate. **This is the baseline you must actually beat** — not "no loop", but what a competent engineer ships today. |
| `fixed-route` | Always take the same action on a fire (always reframe, always escalate). |
| `candidate` | The adaptive policy under test. |

**Factor 3 — TASK STRATUM** (known only where you constructed the tasks):

| Level | Description |
|---|---|
| `solvable-easy` | Should succeed. Detects over-intervention. |
| `solvable-hard` | Succeeds only with good routing. Where the value should show up. |
| `unsolvable` | Cannot succeed. **The control condition for "the task was just hard."** |

### 5.2 The core conditions and exactly what each one diagnoses

You do not need the full cross-product. Eight cells carry the diagnostic load:

| # | Signal | Policy | What this cell is for |
|---|---|---|---|
| 1 | `blind` | `none` | **Unmonitored floor.** What happens with no loop management at all. |
| 2 | `blind` | `blind-heuristic` | **Standard-practice baseline.** What engineers ship today. Every claim is measured against *this*, not against cell 1. |
| 3 | `naive` | `fixed-route` | **Sensor floor.** A cheap proxy under a fixed policy. |
| 4 | `candidate` | `fixed-route` | **Sensor contrast.** Compare to 3: policy held constant, so any difference is attributable to the measurement. |
| 5 | `oracle` | `fixed-route` | **Sensor ceiling.** The best this policy can possibly do. The gap 4→5 is exactly how much your sensor is still losing. |
| 6 | `oracle` | `candidate` | **Controller contrast.** Compare to 5: evidence held perfect, so any difference is attributable to the policy. |
| 7 | `candidate` | `candidate` | **The deployed system.** The number you would actually ship. |
| 8 | `corrupted(ε)` | `candidate` | **Controller robustness.** Sweep ε and watch the policy degrade. |

Run every cell across all three strata, with repeats, and the diagnosis falls out of the comparisons:

| Observation | Diagnosis |
|---|---|
| Cell 5 fails (oracle signal, still bad outcomes) | **The policy is the problem.** No sensor improvement can rescue this. Stop working on measurement. |
| Cell 5 good, cell 4 bad | **The sensor is the bottleneck.** Invest in measurement; the routing is already fine. |
| Cell 6 > cell 5 | The candidate policy genuinely converts evidence into outcomes better than the fixed route. |
| Cell 7 ≈ cell 5 | Your sensor is effectively as good as an oracle *for this decision*. Further sensor work has diminishing returns. |
| Cell 7 ≤ cell 2 | Whatever you have built does not beat a blind heuristic. This is the result most projects never check for. |
| Cell 8 degrades gracefully as ε rises | Robust controller — it hedges against uncertain evidence. |
| Cell 8 falls off a cliff at small ε | Brittle controller that over-trusts its sensor. Dangerous in production, where ε is never zero. |
| Everything fails in `unsolvable` | **The task was hard.** This is *not* loop failure, and reporting it as such is the most common way agent evaluations mislead. |

### 5.3 The subtlety in the unsolvable stratum

On unsolvable tasks, **success rate is the wrong outcome metric** — everything scores zero and you learn nothing. The right metric there is **cost saved**: a good loop should detect futility and abandon early, spending less than an unmanaged run. A system that burns the full budget on an impossible task has failed even though its success rate matches everyone else's.

This is why outcome metrics must be **pre-registered per stratum** before you look at results.

### 5.4 The corrupted-oracle sweep is the most useful cell for engineers

Cell 8 answers a question every engineer building this actually has: **how good does my sensor need to be before this policy pays for itself?**

Sweep ε from 0 (perfect) to 0.5 (useless) and find the crossover where the adaptive policy stops beating the blind heuristic. That gives you a **minimum sensor quality specification** — a target to build against, derived rather than guessed. It also tells you when to stop: if your policy still wins at ε = 0.3, chasing another two points of F1 is wasted effort.

### 5.5 Why you need synthetic data *and* real traces

This is the question that trips people up, so let it be explicit.

**Synthetic data buys you four things you cannot get otherwise:**

1. **Ground truth by construction** — the only way to have an `oracle` condition at all. Labels are not annotated, they are *constructed*: the generator knows which steps recycle because it wrote them that way.
2. **Known difficulty strata** — you can only run the "genuinely hard task" control if you know which tasks are unsolvable.
3. **Controlled signal corruption** — you can only sweep ε if you have a clean signal to degrade.
4. **Cost and repeatability** — no annotation budget, deterministic, and anyone can regenerate it.

**Real traces test the things synthetic cannot:**

1. **Incidence.** A simulator *assumes* the pathology exists. Only real traces tell you whether real agents exhibit it at rates that matter — which is the difference between an interesting mechanism and a useful product.
2. **Domain transfer.** Operating points fitted on curated examples may not survive contact with production distributions. Watch specifically for saturation, where a sensor tuned elsewhere fires on nearly everything and its apparent discrimination collapses.
3. **Independent outcome labels.** Real runs often carry a verifier, a test suite, or a human acceptance decision — an outcome criterion that owes nothing to your sensor or your judges.

**Synthetic proves the mechanism can work. Real proves it matters. Neither substitutes for the other, and a project that only has one of them should say which.**

### 5.6 The failure taxonomy, including the one nobody looks for

| Failure | Signature | Fix |
|---|---|---|
| **Faulty sensor** | Disagrees with a defensible criterion about plateau vs progress. Cell 5 ≫ cell 4. | Better measurement. |
| **Faulty controller** | Right signal, poor route (terminating where reframing would recover). Cell 5 fails. | Better policy. |
| **Wrong objective** | Locally sensible actions optimising the wrong trade-off — minimising tokens when completion is what matters. | Fix the utility function, then re-run. |
| **Genuinely hard task** | Everything fails, including oracle + best policy. | Nothing. Report it as task difficulty, not loop failure. |
| **Wrong construct** | Sensor measures something real that is not the thing that predicts outcomes. Wins Link A, no movement at Link C. | Revisit what you are measuring. |
| **Confounded criterion** | ⚠️ Your ground truth and your sensor **share a method**, so they agree for the wrong reason. | See below — this one is invisible without a specific test. |

That last row deserves its own paragraph because it is the subtlest failure in the whole design and it silently invalidates rankings.

Suppose you label your traces using an LLM judge that reads step text, and your sensor also works on step text. If the judge is largely detecting *textual repetition*, then any lexical sensor agrees with it **by shared method rather than by both being right.** Your ranking now measures agreement-with-the-judge, not construct validity.

**The test:** build deliberately construct-blind oracles — rules that know nothing about information gain, like "is this text similar to the previous step?" — and score them against your labels. If a stupid lexical rule predicts your labels about as well as your best sensor does, your labels are method-confounded. The corroborating check is criterion disagreement: if your label-based ranking and an **independent** outcome criterion (verifier pass/fail) rank sensors in *opposite* orders, trust the independent one.

The general principle, borrowed from psychometrics: **convergent validity requires independent instruments.** Two measurements that share a method are not two pieces of evidence.

### 5.7 Analysis discipline that keeps the result honest

- **Pre-register** the outcome metric per stratum before looking at results.
- **Split by generating source, not by index.** Splitting runs of the same task family across train and test lets a fitted threshold memorise the task rather than the pathology, and inflates held-out numbers dramatically. Split on task, project, or session family.
- **Cluster your statistics on the trace, not the step.** Steps within one run are not independent observations; treating them as such understates uncertainty badly.
- **Report the standard-practice baseline every time.** A blind heuristic tuned in hindsight is a surprisingly strong competitor, and any honest report shows it.
- **Report the no-intervention floor**, so a reader can see how much of the outcome is the loop at all.

---

## 6. What this looks like as a working repository

[Gyre](https://github.com/kareem-soliman-ai/Gyre) is the above, made runnable. Its shape follows directly from the argument:

**Public — everything needed to verify a claim:**

- The **seams**: `MeasurementProvider` (sensors) and the controller interfaces, so nothing is fused.
- **Naive baseline sensors** that are real, usable, and honest about being crude.
- **Labelled synthetic corpora** *with their generators visible*, so you can audit exactly what each case contains rather than trusting a description.
- A **benchmark** that is deliberately generous to challengers: if your sensor returns raw values, the harness sweeps every threshold and reports your best case. Validated instruments get no such favour — they are scored on their own decisions.
- A **published scoreboard**, generated from a bench run rather than hand-written, plus two CI gates: one checking every public claim is tagged to a ledger entry, and one re-deriving the cited figures to make sure they still reproduce. A number that goes stale turns the build red instead of quietly staying wrong.

**Private — the things that make an instrument validated rather than plausible:** fitted operating points, corrected mechanisms, and the labelled corpora they were earned on. Open method, closed instrument. The method is fully described; what stays behind the fence is the calibration, because a measurement that ships its fitted constants is a measurement you can game.

**The invitation is adversarial by design.** Bring your own sensor:

```bash
python scripts/challenge.py --contender yourmodule:build
```

It scores against the published board, per case, with the trap cases shown — deliberately healthy iteration that superficially resembles circling, where firing is a false positive. A pooled win that loses the trap cases is measuring surface form, and the harness shows you that rather than hiding it.

### What is claimed, and what is not

On synthetic ground truth with labels known by construction, the measurement ladder produces a real and reproducible gap between naive proxies and construct-modelling sensors, and that gap propagates into loop cost in replay <!-- claim:GYR-01 -->. On the control side, across cost regimes, adaptive control's worst-case regret is substantially lower than the best fixed policy and dramatically lower than the best blind heuristic — robustness, not peak performance, is the defensible claim <!-- claim:GYR-02 -->. A local instrument also beats a per-step LLM judge on the same synthetic cases at a tiny fraction of the cost, and the judge fails specifically on the construct-subtle cases <!-- claim:GYR-03 -->.

**Every one of those is a synthetic-tier result and is labelled as such.** Real-trace validation is underway and is deliberately held behind an expert-anchoring gate; those numbers are not published, and the repository's claims ledger enforces that mechanically rather than relying on discipline. Some vendored mechanisms have also simply failed under evaluation and were reported as failures rather than quietly dropped — which is the honest signature of a research posture rather than a demo.

---

## 6b. What is already out there, and what is actually different here

Nothing above is claimed as unprecedented. Almost every component has a home discipline, and being explicit about that is part of the argument rather than a concession to it.

**Loop detection already ships.** Several agent frameworks and standalone packages detect stuck loops today. Look closely at what they detect: **iteration**. Repeated tool calls, repeated outputs, a step counter crossing a hand-picked constant. That is a real and useful feature, and it is a different construct from the one described here. The distinction is not "we detect loops better" — it is *what is being measured*: repetition of form versus absence of information gain. A tool that fires on repetition will flag an agent confirming a fix and miss an agent circling through five superficially different framings of the same dead end.

**The architecture is control theory.** Separating an observer from a controller is textbook, and if you have built any observability stack you already separate instrumentation from the logic being instrumented. The contribution here is not the separation. It is naming the **validity obligation** the separation carries: once the sensor is a component, it becomes a measuring instrument, and measuring instruments have to earn their numbers.

**The measurement discipline is psychometrics, and it is old.** Construct validity, reliability, and the distinction between them predate machine learning by decades; the professional standards for educational and psychological testing are the canonical reference. The closest work in ML is the line on **measurement modelling for contested constructs** — Jacobs and Wallach's treatment of fairness measurement is the standard citation, and it makes the same core move: when your target is a latent construct, you owe an explicit account of how your observable operationalises it.

**Runtime psychometric instrumentation for agents is being built right now**, including systems that compute construct scores outside the inference path and feed them to orchestration. That is the same architectural principle. Where this repo tries to add something is not the instrumentation but the **validity evidence for it** — and the honest framing is validating an approach others are also pursuing, not competing with them.

**LLM-as-judge reliability is an active field**, including work showing that judge consistency and judge validity come apart badly. That is the direct antecedent for the qualification machinery here, and it is being extended rather than replaced.

So the defensible claim is narrow and specific:

> **Psychometric construct validity applied to a runtime sensor inside a live control loop** — not a model, not a static benchmark — operationalised as a calibration ladder, tested by factorial attribution with corrupted-oracle and unsolvable-task controls, and disclosed under an open-method/closed-instrument policy.

Each ingredient exists. The combination is what is being offered, and combinations are worth less than inventions — which is why the repo ships the proving ground rather than asking for the benefit of the doubt.

**The strongest objection, stated plainly:** the results here are synthetic-tier. A simulator that assumes the pathology exists cannot prove the pathology matters. Real-trace validation is underway and deliberately unpublished until it is anchored. If you want to attack this work, attack it there — it is where the evidence is genuinely thinnest, and pointing that out costs nothing because the claims ledger already says so.

**On "the discourse moved from loops to graphs":** a loop is a special case of a graph, so nothing here stops applying — it gets worse. In a single loop an invalid sensor produces one bad decision. In a routed topology, an invalid sensor at one node propagates through every downstream routing decision that depends on it. The measurement obligation scales with the graph.

---

## 7. Does any of this translate to prompting?

This is the question everyone asks, and it has a genuine answer with a genuine limit.

### What translates

**Give the model the discriminator, not the symptom.** "Check whether you are looping" invites counting. Instead: *"Before continuing, state what new information the last step produced relative to everything already tried. If you cannot name any, do not repeat the approach."* You are handing over the construct definition, which is the transferable part of the science.

**Require evidence for the self-assessment.** Make the model quote the specific thing that is new — or the specific thing that shows nothing arrived. An unevidenced self-report is an assertion; a quoted one is checkable, and you can verify the quote actually appears in the trace.

**Separate detection from decision, structurally.** One turn (or one agent) assesses whether the loop is still producing information. A different step decides what to do about it. Fusing them in a single prompt reproduces the exact architectural mistake the whole document argues against, just in natural language.

**Give the controller a menu, not a switch.** If your prompt's only response to a plateau is "stop", you have built the bad controller from §4. Spell out the options: reframe, seek information, switch subtask, escalate with a summary of what was tried.

### What does not translate — and this is the important part

**A self-monitoring prompt is a sensor of unknown sensitivity and specificity.** You have no idea how often it correctly catches a stuck loop, or how often it fires on healthy iteration. It has not been calibrated, and *nothing in the prompt can calibrate it* — calibration requires comparing its output to labels it did not produce.

**Worse: the judge is the judged.** When an agent evaluates its own trace in its own context window, the assessment shares the generator's blind spots. The same reasoning that produced the stuck loop is now being asked to notice it. Errors correlate exactly where you need independence. This is the same reason self-consistency is not accuracy, and the reason LLM-as-judge setups need qualification against external labels before their scores mean anything.

So the honest position: **self-monitoring prompts are a reasonable, cheap intervention that may well help — and they are an unmeasured one until you measure them.**

### How to actually find out

Treat your prompt as a sensor and run the design from §5. It is a `candidate` signal like any other:

1. Collect traces, label them against a defensible criterion (ideally not with a judge that shares the prompt's method — see §5.6).
2. Score the prompt's self-assessments against those labels. That is Link A. You now have sensitivity and specificity where before you had a vibe.
3. Hold the prompt fixed, vary the response menu. That is Link B.
4. Measure task outcomes against the blind-heuristic baseline. That is Link C.
5. Run the corrupted-oracle sweep to learn how good the self-assessment has to be before the routing pays.

### The practical recommendation

**Externalise the sensor where you can.** Cheap deterministic signals computed outside the model's context — novelty against everything tried so far, whether new evidence actually arrived, token spend per unit of progress — are independent of the generator by construction. They cannot share its blind spots because they do not share its reasoning. Use in-context self-assessment as a *second, correlated channel*, not as the primary instrument, and where you need a judging model, give it a different model family and a fresh context rather than the generator's own.

**Do you need to build sensors before you can rely on them?** For low-stakes loops where a wrong call costs you one wasted step: no, a naive proxy is genuinely fine, and gold-plating it is waste. For loops where intervention is expensive or the failure is silent: yes — and the intermediate move is to run the sensor in **shadow mode**, logging what it would have done without acting on it, until you have enough paired data to check whether its calls were right. That gives you Link A evidence at zero risk, and it is the cheapest honest thing you can do this week.

---

## 8. The short version

Agent loops are control systems, and we ship them with no instruments. The fix is not a better heuristic; it is separating the parts so they can be tested:

- **Sensor** — measures whether the loop is still producing information. Judged by whether it agrees with a defensible criterion.
- **Controller** — decides what to do about it. Judged by whether it routes well *given* the signal.
- **Outcome** — whether any of it made the task go better. Judged against a baseline someone would actually ship.

Keep them separate and you can ask *which one is broken*. Fuse them and you get an impressive-looking score that tells you nothing about what to fix.

And hold the line on evidence. A detection win is evidence about a sensor, not about your agents. A decimal point is not truth until labels, reliability, and outcomes have earned it. Give away the pattern; earn the number.

---

*Gyre is open at [github.com/kareem-soliman-ai/Gyre](https://github.com/kareem-soliman-ai/Gyre). The proving ground, the baselines, the corpora and the benchmark are all public — including the parts designed to make it easy to beat us. See [docs/challenge.md](challenge.md) for the rules and the standing invitation.*
