# Gyre

**Psychology-grounded loop patterns for AI agents.**

Loop engineering is having its moment. Boris Cherny says he doesn't prompt Claude anymore, he writes loops that prompt Claude. Peter Steinberger's two sentences about designing loops instead of prompts did 6.5 million views. Addy Osmani wrote the field guide. The leverage point has moved from the prompt to the loop, and everyone building agents is now, whether they call it that or not, a loop engineer.

Here is the thing nobody in that conversation has said out loud: this is not a new discipline. It is cybernetic psychology, rediscovered by people who never took the class.

Psychology has been studying loops for sixty-five years. Not execution loops, cognitive loops. The loop a mind runs when it worries at a problem, when it checks its own confidence, when it repairs a relationship that has gone off the rails, when it gets stuck and needs to walk away before the answer arrives. These have names, mechanisms, decades of empirical work, and a hard-won understanding of what separates a loop that helps from a loop that quietly wastes your life. Agent builders are re-deriving fragments of this from scratch, one Reddit post about "why does my agent get stuck" at a time.

Gyre is the taxonomy, translated. Each pattern names its source in the psychological or cybernetic literature, states the mechanism, translates it into a shape you can drop into an agent scaffold, and defines the behavioural signal that tells you whether the loop is working or pathological.

---

## The claim, in one paragraph

An execution loop is: do something, check the result, decide whether to continue. Test, operate, test, exit. That structure is not an engineering invention. It is [TOTE](loops/L0-tote.md), proposed by Miller, Galanter and Pribram in 1960 as the fundamental unit of behaviour, the thing that displaced the reflex arc in psychology. When Steinberger says "do something, check, decide whether to stop," he is describing a TOTE unit. The agentic loop is a TOTE unit with an enormous Operate step. Once you see that, the rest of the psychology of loops becomes available to you: not as metaphor, but as a catalogue of mechanisms that have already been studied, measured, and validated in the one system we understand better than any agent, the human mind.

## What this is

Lightweight, loop-shaped patterns that fit the scaffolds you already write: hooks, monitors, wrappers, memory layers. Not a framework you adopt wholesale. A vocabulary and a set of shapes you borrow from.

Every entry follows the same format:

> **Source** (the psychology) → **Mechanism** (what it does in a mind) → **Agent translation** (what it does in an agent) → **Signal** (how you measure it) → **Exit condition** (when the loop should stop or change) → **Shape** (where it fits in a scaffold)

## What this is not

Not a cognitive architecture. ACT-R and SOAR spent decades on the monolithic route, and nobody shipping agents today adopts a monolith. Gyre is deliberately the opposite: small patterns shaped like the hooks people already write, each one useful on its own, none of them requiring you to buy the whole thing.

Not a set of performance claims. No detector in this repository ships with a "saves you 40% of tokens" number attached, because none of them have earned one yet. When a pattern has run on real agent traces and produced a result worth defending, that result will be stated plainly, with the caveats intact. Until then, these are patterns and hypotheses, clearly labelled as such.

---

## The catalogue

Start at the [loop index](loops/INDEX.md). The short version:

| # | Loop | Psychology source | What it catches in an agent |
|---|------|-------------------|------------------------------|
| [L0](loops/L0-tote.md) | TOTE | Miller, Galanter & Pribram (1960); Carver & Scheier | The loop itself, as the unit of behaviour. Framing. |
| [L1](loops/L1-rumination-vs-reflection.md) | Rumination vs Reflection | Nolen-Hoeksema; Watkins (2008) | Retrying the same fix with cosmetic variation. Iteration that recycles instead of learns. |
| [L2](loops/L2-metacognitive-calibration.md) | Metacognitive Calibration | Nelson & Narens (1990) | Confidence that never gets checked against outcomes. |
| [L3](loops/L3-rupture-and-repair.md) | Rupture and Repair | Safran & Muran | The human quietly rewriting your output instead of telling you it is wrong. |
| [L4](loops/L4-zeigarnik-intentions-register.md) | Zeigarnik Intentions Register | Zeigarnik (1927); Masicampo & Baumeister | Abandoned threads the agent forgets it ever opened. |
| [L5](loops/L5-incubation-einstellung-breaker.md) | Incubation / Einstellung Breaker | Wallas (1926); Luchins; Sio & Ormerod (2009) | Fixation that more effort makes worse, not better. |
| [L6](loops/L6-habituation-orienting.md) | Habituation / Orienting | Sokolov; Thompson & Spencer | Monitoring pass 400 as if it were pass 1. |
| [L7](loops/L7-meta-loop.md) | The Meta-Loop | Explore-exploit; control theory | Which loop should run now, and when to switch. |

Plus a [backlog](loops/backlog.md) of one-line sketches waiting for someone to pull on them.

**Start here if you build agents:** [L1, Rumination vs Reflection](loops/L1-rumination-vs-reflection.md). It is the one every agent already suffers from, and the one with the clearest signal. Same surface behaviour as productive iteration, opposite outcome. The discriminator psychology settled on is not how many times you loop, it is whether each pass generates new information or recycles the old.

---

## The three tiers

Gyre is built in three layers, and only the first is in this repository today.

**Tier 1, the patterns (here, open).** The documented catalogue: source, mechanism, translation, signal, exit, shape. This is not defensible as a secret and it is not meant to be. Once a pattern is named, anyone can restate it. Its value is that it exists, that it is attributed, and that it gives the loop-engineering conversation a shared language. This ships open under CC BY, and it ships first.

**Tier 2, the instruments (staged).** The detectors that actually score loop quality from live agent behaviour. A rumination detector is not a pattern, it is a measurement instrument: it claims to detect a latent property (is this loop productive) from noisy, time-unfolding behaviour. That is a real measurement problem with real validity requirements, and getting it wrong quietly is worse than not measuring at all. The method is described openly in each pattern doc. The scoring internals, thresholds, and validation pipelines stay closed until they have been validated on real traces. Method open, pipeline closed.

**Tier 3, the controller (not here).** The meta-loop that decides which loop runs when. That is a hard problem with its own research lineage, and it is not rebuilt in this repo. When it arrives it will be as a described interface, not a giveaway.

If that fence sounds cautious, it is deliberate. The patterns are the gift. The measurement is the craft. Giving away the first does not require giving away the second, and a detector that reports a confident number it has not earned is not a contribution, it is a liability.

---

## Install

The v0.1 package ships interfaces and vocabulary, not detectors. It gives you the types to write your own loop monitors against a common shape while the instruments mature.

```bash
pip install -e .
```

```python
from gyre import LoopMonitor, LoopVerdict, ExitReason
```

See [`src/gyre/`](src/gyre/) for the interfaces and [`docs/pattern-template.md`](docs/pattern-template.md) for how a pattern doc is structured if you want to contribute one.

---

## Credit where it is due

I come at this from a psychological science background, with graduate training in psychometrics and measurement theory. I am not a psychologist, and nothing here is clinical advice about anything. What I have is a lens: which loops does a mind actually run, what discriminates a productive loop from a pathological one, and how do you measure loop quality from behaviour over time. That last question is the one I care about most, and it is the hardest.

The psychology cited here is other people's work. I have tried to cite it accurately and translate it honestly. Where an analogy between a human loop and an agent loop breaks down, the pattern doc says so, because a translation that hides its seams is worse than no translation.

I build with AI in the loop and disclose it as a matter of principle. The framing and the interpretive calls are mine. The drafting and the plumbing involve AI collaboration.

---

## The open question

Here is what I actually want from putting this out.

**If you are a psychologist or study cognition:** which loops am I missing? Sixty-five years is a lot of literature and this catalogue is eight entries. What mechanism have you spent your career on that would translate into an agent and that no engineer has thought to look for?

**If you build agents:** which of these have you already built without knowing it had a name? Every one of these patterns exists in the wild as a hack somebody wrote at 2am to stop their agent doing something stupid. I want to know which hacks map onto which mechanisms, because that is where the catalogue earns its keep.

Open an issue, start a discussion, or just tell me I have got one wrong. The whole point of naming these loops is to find out which ones are real.

---

*Licensed dual: code under [Apache-2.0](LICENSE), the written catalogue under [CC BY 4.0](LICENSE-docs). Cite it if you use it, and the lineage stays legible for the next person.*
