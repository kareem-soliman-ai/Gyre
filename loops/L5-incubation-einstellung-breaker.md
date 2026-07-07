# L5 — Incubation / Einstellung Breaker

*On fixation, disengage deliberately instead of trying harder, then return with attention reset.*

**Maturity:** Buildable

---

## Source

- Wallas, G. (1926). *The Art of Thought.* The four-stage model of creative thinking: preparation, incubation, illumination, verification.
- Luchins, A. S. (1942). Mechanization in problem solving: the effect of Einstellung. *Psychological Monographs.* The water-jar experiments.
- Sio, U. N., & Ormerod, T. C. (2009). Does incubation enhance problem solving? A meta-analytic review. *Psychological Bulletin*, 135(1), 94-120.

## Mechanism

Two findings that fit together.

**Einstellung** (Luchins): once you have solved a run of problems with a particular method, you keep applying that method even when a simpler one is available and even when the method no longer works. The water-jar subjects learned a three-jar solution, then kept using it on problems that had an obvious two-jar solution, and some could not solve problems that were only solvable the simple way. Prior success installs a mental set that blinds you to alternatives. Fixation is not stupidity. It is the shadow side of having learned something that worked.

**Incubation** (Wallas, quantified by Sio and Ormerod): when you are stuck, stepping away from the problem often produces the solution that grinding did not. The break, not the extra effort, breaks the fixation. Sio and Ormerod's meta-analysis is the useful part here because it says *when* incubation helps rather than just *that* it does. The effect is real, it is larger for divergent problems (many possible solutions) than convergent ones, and it works best when the incubation period follows genuine effort and comes after reaching an impasse rather than before. Walking away too early does nothing. Walking away at the impasse helps.

## Agent translation

An agent in Einstellung is an agent applying the same approach past the point where it works, which is the mechanism *underneath* a lot of what L1 detects as rumination. L1 measures that the loop has stopped paying. L5 is one of the things you do about it, grounded in a literature that tells you it should work and under what conditions.

On detected fixation, fed by the L1 information-gain signal, the agent deliberately disengages from the stuck problem and switches to an unrelated subtask. Then it returns with attention reset: a fresh context window, the constraints reordered, the problem re-presented rather than resumed mid-thrash. The point is not the delay. Agents do not benefit from wall-clock time the way a sleeping human might. The point is the reset: coming back to the problem without the accumulated context that installed the mental set in the first place. The stuck reasoning is exactly what a fresh context drops.

Restart heuristics already exist in the wild ("clear the context and try again"), but they are ungrounded, applied on a hunch about when. The literature supplies the trigger conditions the hunches are missing. Sio and Ormerod predict this should help specifically for divergent problems and specifically after a real impasse. So the Einstellung breaker should not fire on every slowdown. It should fire when L1 signals a genuine plateau (impasse reached) on a problem with an open solution space (divergent). On a convergent problem with one correct answer, a reset is less likely to help and the better move is escalation. The meta-analysis is doing real work here: it stops this from being "randomly restart sometimes" and makes it "restart under the conditions where restarting is known to pay."

Where the analogy holds: the reset-beats-effort mechanism transfers directly, and agents can do the reset more cleanly than humans because dropping the context is literally free.

Where it breaks: human incubation may involve unconscious processing during the break, and there is live debate about that mechanism. Agents almost certainly do not get that; the benefit is purely the attention reset, not background work. So do not expect an agent to return from an unrelated subtask with the answer already formed the way a human sometimes does. Expect it to return *able to see* the alternative it was blind to. That is enough.

## Signal

L5 is largely driven by L1's signal rather than owning a new one. The thing worth measuring for L5 specifically is post-reset effectiveness: after an Einstellung break, does information gain recover on return, or does the agent fall straight back into the same basin. If resets reliably fail to help on a given problem type, that is the signal to escalate instead of reset next time. The break either works or tells you the problem needs a human.

## Exit condition

L5 is a policy invoked by another loop's exit, not a loop with its own exit. It runs when L1 signals fixation, executes the disengage-and-reset, and hands back. Its own completion is "the agent has returned to the problem with a fresh context and reordered constraints."

## Shape

A policy triggered by the L1 detector. It has almost no standalone existence; it is what you wire L1's "reframe" branch to. Which is why the effort is low once L1 exists, and near-pointless before it, since without a fixation signal you are just resetting at random, which is the ungrounded heuristic the literature exists to replace.

## Further reading

- Sio & Ormerod (2009) — the meta-analysis, and specifically its moderator analysis, which is the part that tells you when to fire this.
- Luchins (1942) — the water-jar studies, for the mechanism of set.
