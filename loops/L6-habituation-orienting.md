# L6 — Habituation / Orienting

*Attend to change, habituate to repetition, fire only on deviation from a learned baseline.*

**Maturity:** Buildable

---

## Source

- Sokolov, E. N. (1963). *Perception and the Conditioned Reflex.* The orienting response and the neuronal model of the stimulus.
- Thompson, R. F., & Spencer, W. A. (1966). Habituation: a model phenomenon for the study of neuronal substrates of behavior. *Psychological Review*, 73(1), 16-43. The nine parametric criteria that define habituation.

## Mechanism

Present a novel stimulus and an organism orients: attention turns, arousal rises, resources engage. Present the same stimulus again and again and the response shrinks. This is habituation, and it is one of the most basic and universal forms of learning, present from single cells to humans.

Sokolov's insight was that habituation is not fatigue. The nervous system builds a **neuronal model** of the expected stimulus, and the orienting response fires in proportion to the mismatch between what arrives and what the model predicts. A fully habituated stimulus matches the model, so it produces nothing. Change the stimulus, even reduce its intensity, and the response returns instantly. This is **dishabituation**, and the fact that a weaker stimulus can trigger it proves the mechanism is prediction-mismatch, not exhaustion. The system is not tired. It has stopped predicting anything new, and it re-engages the instant the world violates its model.

Thompson and Spencer's nine criteria (habituation is stimulus-specific, recovers over time, shows faster re-habituation on repeated series, and so on) are, in effect, a specification. If you are building something you want to call habituation rather than just a decay counter, they tell you what behaviours it has to exhibit.

## Agent translation

Monitoring agents have no habituation and it makes them useless at monitoring. An agent watching a log treats pass 400 exactly like pass 1: same processing, same attention, same cost, on a signal that has said nothing new for hours. It cannot tell you what changed because it was never modelling what was stable. Worse, an agent tuned to react to everything will drown you in alerts about the normal, and an agent tuned down to cope will miss the one deviation that mattered.

The pattern is a habituation filter over any monitored channel. It builds an adaptive baseline, the neuronal-model analogue, of what that channel normally looks like. It suppresses response to input that matches the baseline, so the steady state produces silence. And it fires, dishabituates, on deviation from the baseline, not on absolute level. The alert is not "the log has an ERROR line," it is "the log is doing something it does not usually do." That is the orienting response: attention allocated to novelty, defined as mismatch against a learned model of normal.

The dishabituation property is the valuable and easy-to-miss part. A naive decay counter that just stops reporting a repeated signal will also stop reporting when that signal changes, because it has decayed. Sokolov's mechanism does the opposite: the more thoroughly it has habituated to the baseline, the sharper its response to a violation, because the model is more confident. Build the filter so that a stable channel becoming even slightly irregular re-engages attention immediately. That is the whole point, and it is what separates this from a mute button.

Where the analogy holds: extremely well. This is one of the most mechanical patterns in the catalogue, prediction-mismatch attention allocation, and it is exactly what ambient monitoring agents lack.

Where it breaks: biological habituation has quirks (spontaneous recovery, potentiation of the response under high arousal) that you may or may not want. Thompson and Spencer's criteria are a menu, not a mandate. You probably want stimulus-specificity and dishabituation; you may not want spontaneous recovery resetting your baseline overnight. Take the criteria that earn their place for the monitoring job and leave the rest.

## Signal

**Deviation from the adaptive baseline, per monitored channel.** The response magnitude is the size of the mismatch between current input and the learned model of that channel. The quality of the loop is whether it stays silent on genuine repetition and fires on genuine deviation, which is a two-sided error you can measure: false alarms on stable input, and misses on real change. A well-built habituation filter drives both toward zero, whereas a threshold alert can only trade one for the other.

## Exit condition

Standing filter, no exit. Per-channel, the "exit" is habituation itself: a channel that stabilises falls silent. Deviation re-engages it. The loop runs for as long as the monitoring does.

## Shape

A filter for ambient and monitoring agents, sitting between the raw channel and the agent's attention. The agent only sees what dishabituates. Everything the baseline predicts is absorbed before it reaches the agent's context, which is also a large context saving as a side effect.

## Further reading

- Thompson & Spencer (1966) — the nine criteria, useful as an implementation checklist.
- Sokolov (1963) — the neuronal-model account, for why dishabituation to a weaker stimulus is the tell that this is prediction, not fatigue.
