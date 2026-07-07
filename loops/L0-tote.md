# L0 — TOTE

*The ancestral pattern. Framing only, no code.*

**Maturity:** Framing

---

## Source

Miller, G. A., Galanter, E., & Pribram, K. H. (1960). *Plans and the Structure of Behavior.* New York: Holt, Rinehart & Winston.

Extended by the control-theory tradition in psychology, notably Carver, C. S., & Scheier, M. F. (1981, 1998) on self-regulation as a hierarchy of feedback loops.

## Mechanism

TOTE stands for **Test, Operate, Test, Exit**. You test the current state against a goal. If there is a mismatch, you operate to reduce it. You test again. When the mismatch is gone, you exit.

The reason this mattered in 1960 is easy to miss now. The dominant model of behaviour was the reflex arc: stimulus in, response out, a straight line. Miller, Galanter and Pribram argued that the fundamental unit of behaviour is not the arc but the loop. Behaviour is organised around feedback against a goal, not around triggered responses. A person hammering a nail is not emitting hammer-responses to nail-stimuli. They are running a loop: is the nail flush (test), no, so strike it (operate), is it flush now (test), yes, stop (exit). TOTE put the feedback loop, borrowed openly from Wiener's cybernetics, at the centre of psychology.

TOTE units nest. The Operate step of a high-level loop ("build the fence") is itself a TOTE loop ("drive this post"), whose Operate step is another ("swing the hammer"). Behaviour is a hierarchy of loops inside loops, each one testing against its own goal.

## Agent translation

Read the definition of an agentic loop that the loop-engineering writers converged on in 2026: do something, check the result, decide whether to continue or stop. That is Test-Operate-Test-Exit with the labels filed off. The agentic loop is a TOTE unit.

What makes the agent case distinctive is the size of the Operate step. In the hammer example, Operate is a single motor action. In an agent, Operate can be "write a module, run the tests, read the failures, patch, rerun," an entire sub-hierarchy of loops that the outer loop treats as one move. The agent's Operate step is where all the other loops in this catalogue live. L1 through L6 are things that can go right or wrong *inside* the Operate step of a larger TOTE unit. L7 is the loop that chooses which Operate to run.

Where the analogy holds: the loop, not the single action, is the right unit of analysis for agent behaviour. If you reason about an agent as a sequence of tool calls, you miss the structure. If you reason about it as nested TOTE units, the failure modes become visible.

Where it breaks: TOTE assumes the Test is cheap and reliable. In a human hammering a nail, the test (is it flush) is a glance. In an agent, the Test is frequently the hardest part. "Did this actually work" can be more expensive and more error-prone than the Operate that preceded it. Every writer on loop engineering says the same thing: the craft is in making the check real. TOTE names the check as load-bearing. It does not tell you how to make it trustworthy. That is what the rest of the catalogue is for.

## Signal

None. This entry exists to make the historical claim and to give the other loops a common frame. If you want a signal, the honest one is diagnostic: for any agent loop, can you point to the Test, the goal it tests against, and the Exit condition it uses? If you cannot find the Test, the loop does not have one, and that is your first bug.

## Exit condition

Not applicable. TOTE is the frame, not a loop you run.

## Shape

A section in a README. A way of seeing. When you next debug an agent that will not stop, or stops too early, ask what its Test is testing and whether the Exit condition is real. That question is L0 doing its job.

## Why this is L0

Everything downstream assumes the loop is the unit. L0 earns that assumption by pointing at the sixty-five-year-old paper that made it, in psychology, before anyone was engineering agents. The loop engineers are right that the loop is the thing. They are standing on Miller, Galanter and Pribram without knowing the building has a foundation.

## Further reading

- Miller, Galanter & Pribram (1960), *Plans and the Structure of Behavior* — the primary source.
- Carver & Scheier (1998), *On the Self-Regulation of Behavior* — the loop hierarchy as a theory of motivation and affect.
- Wiener, N. (1948), *Cybernetics* — the feedback loop that TOTE imported into psychology.
