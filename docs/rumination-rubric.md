# Rumination Scoring Rubric

The construct definition used to label agent traces for the L1 evaluation. It is
public on purpose: the labelling rubric is method, not moat. The validated
production sensor is the protected part; how you decide ground truth is open, so
that anyone can reproduce the comparison and build their own labelled corpus.

This rubric is the exact text a judge scores against (`gyre.labeling.RUMINATION_RUBRIC`).

## The construct

Rumination and reflection look identical on the surface: both are an agent
iterating on a problem. The discriminator is **information gain per step, not
iteration count**. A reflective agent might loop ten times productively; a
ruminative one three times uselessly. What separates them is whether each step
adds new information relative to what has already been tried.

- **Reflection (not ruminating):** the step introduces new information, reframes
  the problem, narrows the space, or responds to genuinely new evidence.
- **Rumination (ruminating):** the step recycles the same content, retries a fix
  with only cosmetic variation, re-asserts the same conclusion, or produces the
  affect of progress with no substance.

## Score a step as ruminating when

In the context of the steps before it, the step does not add new information. Concretely:

- A near-identical approach to a previous step with only renamed variables,
  reordered lines, or reworded prose.
- Retrying something that already failed the same way, without a changed hypothesis.
- Restating the plan or the problem without advancing it.
- Circling the same fix family after it has stopped working.

## Do NOT score as ruminating

- A genuinely new approach, even if it superficially resembles a prior one.
- A legitimate retry after new information arrived (a dependency installed, a new
  error message, a clarification from the user).
- A first attempt at anything.

## Why the label is contextual

A step is not ruminating in isolation; it is ruminating **relative to the steps
before it**. The judge is always given the prior steps as context. This matches the
construct: rumination is defined by the lack of gain *over prior iterations*, so a
single step can only be scored against its history.

## The confounds to hold in mind

The reason this needs a judge (or a careful sensor) rather than a surface metric is
that the cheap proxies all break here:

- **Lexical similarity** is fooled by renaming: a semantically identical retry with
  fresh variable names looks novel.
- **Iteration count** is the wrong axis entirely: it cannot tell ten productive
  loops from three ruminative ones.
- **Diff size** rewards thrashing: an agent that rewrites everything each pass looks
  maximally novel while getting nowhere.

The rubric asks the judge to score the underlying construct (information gain), not
any of these proxies. That is also exactly why a naive sensor scored against a
rubric-labelled corpus tends to lose: the labels track the construct, and the proxy
tracks a surface that comes apart from it.

## Using the rubric

- To label at scale: `gyre.labeling.OpenRouterJudge` sends this rubric plus each
  step and its context to an LLM and parses a verdict.
- To trust the labels: hand-score a small set, then `gyre.labeling.qualify_judge`
  checks whether a candidate judge agrees with you well enough (Cohen's kappa and
  Gwet's AC1) to be trusted to scale. You label a handful; the qualified judge
  labels the rest.
