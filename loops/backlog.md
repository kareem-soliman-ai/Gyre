# Backlog

Loops sketched in one line each. Not built, not fully worked through, open for anyone to develop into a full pattern doc using the [template](../docs/pattern-template.md). If one of these is your field, take it.

## Sketched

**Effort-justification loop.** Source: Festinger's cognitive dissonance; the sunk-cost and escalation-of-commitment literature (Staw). Mechanism: the more effort invested in a course, the harder it is to abandon, and the investment itself becomes a reason to continue. Agent translation: an agent that has written a lot of code down one path defends that path against evidence it is wrong, rewriting and patching rather than reverting, because the sunk cost is doing the arguing. Signal candidate: divergence between how long an approach has been pursued and its information gain, an escalation-of-commitment detector for agents defending sunk-cost code.

**Social referencing loop.** Source: developmental psychology, the infant checking a caregiver's face to appraise an ambiguous situation (Sorce, Emde, Campos & Klinnert, 1985). Mechanism: under uncertainty, resolve it by reading a trusted other's appraisal before acting. Agent translation: a multi-agent pattern where an uncertain agent, rather than guessing or halting, checks a designated trusted agent's read of the situation and updates on it. Distinct from simple delegation: the point is appraisal of ambiguity, not handing off the task. Signal candidate: whether social-referencing checks are triggered by genuine uncertainty (high entropy) rather than reflexively.

**Retrieval-practice loop.** Source: the testing effect (Roediger & Karpicke, 2006); spaced retrieval. Mechanism: retrieving information strengthens it more than re-reading does, and spacing the retrievals strengthens it further. Agent translation: an agent that periodically self-tests against its own memory store rather than passively re-reading it, surfacing what it can and cannot reconstruct, and spacing those self-tests to reinforce what matters. Signal candidate: reconstruction accuracy over spaced intervals, and whether the loop allocates practice to the items that most need it.

## How to promote a backlog item

1. Copy [docs/pattern-template.md](../docs/pattern-template.md).
2. Fill in the source properly. Cite the primary literature, not a summary of it.
3. Be honest in the "where the analogy breaks" section. A pattern that hides its seams is worth less than one that shows them.
4. Mark maturity accurately. If it makes a measurement claim, it is an instrument, and it does not get to state numbers until it has been validated. See [docs/measurement-stance.md](../docs/measurement-stance.md).
5. Open a PR, or an issue if you want to discuss the framing first.

## Adding a loop that is not here

The catalogue is eight entries against sixty-five years of literature. It is almost certainly missing more than it contains. If you know a mechanism, from cognition, development, clinical, social, or comparative psychology, that would translate into an agent loop, propose it. The [contributing guide](../CONTRIBUTING.md) has the full process. The bar is not "is it in a textbook," it is "does it name a real loop a mind runs, and does the translation to an agent hold up when you push on it."
