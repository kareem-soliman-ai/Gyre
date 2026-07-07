# L2 — Metacognitive Calibration

*Confidence that gets checked against outcomes and steers what happens next.*

**Maturity:** Buildable

---

## Source

- Nelson, T. O., & Narens, L. (1990). Metamemory: a theoretical framework and new findings. *The Psychology of Learning and Motivation*, 26, 125-173. The monitoring-and-control framework.
- Fischhoff, B., Slovic, P., & Lichtenstein, S. (1977). Knowing with certainty: the appropriateness of extreme confidence. *Journal of Experimental Psychology: Human Perception and Performance.* The calibration literature.
- The judgments-of-learning tradition: how a learner's predicted recall compares to actual recall.

## Mechanism

Nelson and Narens drew the distinction that the whole field turns on: **monitoring** versus **control**. The meta level monitors the object level (how well do I know this, how likely am I to succeed) and the meta level controls the object level (study more, stop, switch strategy). Metacognition is these two flows. Monitoring is information going up, from the task to the model of the task. Control is information going down, from the model to the behaviour.

Calibration is the quality of the monitoring. A well-calibrated person who says "70% confident" is right about 70% of the time. Fischhoff's work showed humans are frequently badly calibrated, systematically overconfident at the high end. The point that matters for agents is the loop: monitoring produces a confidence judgment, the outcome either confirms or disconfirms it, and that discrepancy updates the model that produces the next judgment. Calibration is not a static trait. It is a loop that either tightens over time or does not.

## Agent translation

Here is a distinction worth holding onto, because it is where agents can do something the literature mostly has not. LLM calibration is studied heavily as a **static property**: is the model's stated confidence well-correlated with its accuracy on a benchmark, averaged over a fixed set. That is calibration-as-property. What is far less explored is calibration-as-loop: an agent that states P(success) before an attempt, records the outcome, updates a running calibration model, and lets that model change what it does next.

The loop version is the interesting one because it closes control. Before each attempt, the agent states a probability of success. After, the outcome updates a rolling calibration curve. And critically, the current calibration steers behaviour: when confidence is low, route to information-seeking (read more of the codebase, ask a question, run a diagnostic) instead of committing to an action. When confidence is high and calibration says high-confidence predictions have been reliable, act. The self-model is not a report you read at the end. It is a governor that is wired into the next decision.

Where the analogy holds well: the monitoring/control split maps cleanly onto an agent that separates "assess the situation" from "act on it," and the loop structure is straightforward to implement because agents already produce confidence-like signals.

Where it breaks: an LLM's stated confidence is not a readout of an internal probability the way a human's "I'm pretty sure" gestures at something felt. It is a token distribution shaped by training, and it can be confidently wrong in ways that are stable rather than random, which is worse. So the calibration loop cannot assume the raw confidence is meaningful. Part of what the running calibration model is *for* is to learn the mapping from stated confidence to actual reliability for this agent, on this kind of task, which may be quite far from the diagonal. The loop can correct a miscalibrated source. It cannot assume a calibrated one.

## Signal

- **Brier score over a rolling window.** The standard proper scoring rule for probabilistic predictions. Lower is better; it penalises both overconfidence and underconfidence. A rolling window rather than a lifetime average, because an agent's calibration on early easy tasks tells you little about its calibration now.
- **Confidence-conditional action policy.** Not just "how calibrated," but "does the calibration change behaviour." The signal that the loop is doing its job is that low-confidence states actually route differently from high-confidence ones. A calibration model that never touches the control flow is monitoring without control, which Nelson and Narens would tell you is only half the system.

## Exit condition

This is not an exit loop. It is a standing governor that runs for the life of the agent. It does not terminate; it steers. The nearest thing to an exit is a meta-signal: if calibration is not improving over a long window, that is itself information, either the task is genuinely unpredictable or the agent's confidence signal carries no usable information, and both are worth surfacing.

## Shape

A wrapper around the agent's decision point. It intercepts the "about to attempt" moment to record a prediction, intercepts the "attempt resolved" moment to record an outcome, and exposes the current calibration to the routing logic. It composes naturally with L1: the information-gain signal from rumination detection and the calibration signal together tell you both whether the loop is learning and whether the agent knows it.

## Further reading

- Nelson & Narens (1990) — the monitoring/control framework in full.
- Guo et al. (2017), "On Calibration of Modern Neural Networks" — the machine-learning side, for how calibration-as-property is usually measured, and the gap this loop tries to close.
