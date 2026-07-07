# Loop Engineering Is Cybernetic Psychology Rediscovered

The framing essay. This is the argument the whole library rests on. If you only read one thing beyond the README, read this.

---

## Two conversations that are the same conversation

In June 2026, a way of talking about AI agents crystallised. Peter Steinberger wrote that you should stop prompting coding agents and start designing loops that prompt them. Boris Cherny said he does not prompt Claude anymore, he writes loops that prompt Claude and figure out what to do. Addy Osmani wrote the field guide and gave it a name: loop engineering. The leverage point in working with agents had moved from the prompt to the loop, and the craft was now in designing the control system, not the instruction.

The definition everyone converged on for an agentic loop is this: do something, check the result, decide whether to continue or stop. The whole art, they agreed, is in making the check real and knowing when to stop.

In 1960, three psychologists wrote a book called *Plans and the Structure of Behavior*. Miller, Galanter and Pribram proposed that the fundamental unit of behaviour is not the reflex arc, the stimulus-response line that had dominated psychology, but the feedback loop. They called their unit TOTE: Test, Operate, Test, Exit. Test the current state against a goal. If it does not match, operate to reduce the gap. Test again. When it matches, exit.

Do something, check the result, decide whether to continue. Test, operate, test, exit. These are the same structure. The loop engineers of 2026 rediscovered, and gave a new name to, the organising insight of cognitive psychology from sixty-five years earlier. The agentic loop is a TOTE unit with an enormous Operate step.

## Why this is more than a cute coincidence

If it were just that one definition matched, it would be a footnote. The reason it matters is what comes *with* the loop once you accept it as the unit of behaviour.

TOTE did not arrive alone. Miller, Galanter and Pribram borrowed it openly from Norbert Wiener's cybernetics, the science of control and communication in animals and machines. Cybernetics is the study of feedback loops as such: how a system uses the gap between its goal and its state to steer itself, how loops nest, how they can be stable or run away, how a controller decides which loop to run. When psychology adopted the feedback loop as its unit, it inherited an entire apparatus for reasoning about loops, and then spent sixty-five years populating it with specific, empirically studied loops that human minds actually run.

Rumination and reflection: two loops that look identical and diverge on whether each pass generates information. Metacognitive calibration: the loop that checks the mind's confidence against outcomes and steers behaviour accordingly. Rupture and repair: the loop that detects when a working relationship has broken and moves to fix it. The Zeigarnik tension system: the loop that keeps an unfinished intention active until it is closed. Incubation: the loop that breaks a fixation by disengaging rather than pushing harder. Habituation: the loop that stops responding to the expected and fires on the novel. Explore-exploit: the meta-loop that decides which loop should run now.

Every one of these is a loop. Every one has a mechanism, decades of measurement, and a hard-won understanding of what makes it go right or wrong. And every one has a direct analogue in the failure modes agent builders are hitting right now and solving from scratch, one "why does my agent get stuck" thread at a time.

## What the psychologist's lens actually adds

Here is the part worth being precise about, because it is easy to overclaim. The loop engineers are not doing anything wrong. They are building good loops, and some of what they build maps onto the psychology beautifully without anyone having planned it. The claim is not that they are missing something obvious. It is that there is a resource available to them that they are not using, because they came to loops through cybernetics-via-engineering rather than cybernetics-via-psychology, and the psychology branch spent sixty-five years on a question the engineering branch has barely started: **what discriminates a productive loop from a pathological one, and how do you measure that from behaviour over time.**

Take the most common agent-loop fix: stop after N identical retries. Fingerprint the tool calls, bail on the third match. It works. It is also a blunt instrument, and psychology can tell you exactly why. The response-styles literature spent decades on the fact that repetition count is the *wrong* discriminator between productive and unproductive iteration. A reflective mind might loop ten times productively; a ruminative one three times uselessly. The thing that separates them is not how many times they loop, it is whether each pass generates new information. An agent can rephrase enough to dodge a fingerprint while making zero progress, and it can legitimately retry a near-identical action after new information arrived. Repetition detection misses both. Information gain catches both. That is not a metaphor. It is a better discriminator, and it is sitting in a literature the loop engineers have not read because nobody told them it was theirs.

That is the whole thesis in one example. Not "engineers are wrong." Rather: engineers are re-deriving, in fragments, a taxonomy that already exists in complete and validated form, in a field they never had reason to check. The bridge is worth building because the far side is already built.

## Where the bridge holds and where it does not

An honest framing has to say where the analogy fails, or it becomes exactly the kind of pop-psychology-for-engineers that deserves the eye-roll it would get.

It holds at the level of **structure and discriminator**. The loops are real, the mechanisms transfer as shapes, and the discriminators psychology found (information gain, prediction mismatch, calibration against outcomes, closure-or-plan) are genuinely better than the proxies engineers reach for first. This is the transferable part, and it is substantial.

It breaks at the level of **cause and substrate**. Human loops ride on affective machinery agents do not have. A person ruminates because they are anxious; an agent ruminates because its search collapsed into a basin and nothing measured the collapse. A person feels the Zeigarnik tension of an open loop as discomfort that drives them to close it; an agent feels nothing and has to be engineered to resurface the loop deliberately. A therapeutic alliance is two parties with feelings; the human-agent dyad is asymmetric, and importing the emotional language too literally would make an agent perform concern it does not have, which is worse than ignoring the rupture. So you take the loop and the discriminator, and you leave the aetiology. Every pattern doc in this catalogue names its own seam for exactly this reason.

## The measurement is the point

One more thing, because it is where this stops being an essay and becomes a research programme. The easy half of this is the taxonomy: name the loops, cite the sources, translate the shapes. That half ships open, and it should, because naming is cheap and attribution is the asset.

The hard half is the measurement. Detecting from live behaviour that a loop is ruminating, that an alliance has ruptured, that a monitored channel has genuinely deviated, these are latent-construct measurement problems, and psychology's other great contribution, the one nobody outside it appreciates enough, is a century of knowing how easy it is to measure a latent construct badly and how much work validity actually takes. A rumination detector that fires on healthy iteration is not a neutral bug. It trains you to distrust the one signal that could have helped. So the measurement layer describes its method openly and holds its validated scoring until the validation exists. Give away the pattern. Earn the number. That discipline is itself part of what the psychologist's lens brings, and it is the part most worth keeping.

## So what

If you build agents, the offer is concrete: here is a catalogue of loops your agents run, named and sourced, with the discriminators that separate the good version from the pathological one, drawn from a field that studied exactly this for longer than the field of AI has existed. Borrow the shapes. Argue with the translations. Tell me which ones you have already built without knowing they had a name.

And if you study minds, the offer runs the other way: agent loops are a new preparation for old questions. An agent that ruminates is a rumination you can instrument completely, log exhaustively, and intervene on freely, in a way no human subject will ever permit. The loops you have spent careers on have a new place to be tested. Which one would you point at an agent first?
