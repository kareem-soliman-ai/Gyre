# Reviewer 2 design audit

## Recommendation

Proceed as a qualification pilot, not as a performance claim.

## Major concerns and responses

1. **The intervention may be the output schema, not the skill.** The
   template-only arm isolates this. The primary comparison is full skill versus
   template, with bare and v1.1 as contextual controls.
2. **Question spam could masquerade as recall.** Joint pass requires high
   recall, precision of at least 0.75, and no more than one unmatched question.
3. **A model could copy fashionable language without controlling anything.**
   Exact runtime probes require task-specific routes and interruption decisions.
4. **The semantic matcher may misclassify paraphrases.** Patterns are frozen
   before calls. Unmatched questions are retained for a transparent manual
   sensitivity audit but cannot retroactively change the primary score.
5. **The common envelope leaks target constructs.** This biases differences
   toward zero but enables deterministic comparison. Claims are limited to
   added value under an explicit developer contract.
6. **Capability is latent and cannot be established here.** The experiment
   scores separation and evidence policies, not actual human or system
   capability.
7. **N is too small for decisive inference.** Promotion uses practical gates,
   paired effects, and model-level non-regression. P-values remain descriptive.

## Simplest alternative explanation for a positive result

The full skill may merely restate exact fields more reliably than the templates,
without producing a useful controller. Exact task-specific probes and hidden
fact revelation reduce, but do not eliminate, this explanation. A later
implementation-bearing study is required.
