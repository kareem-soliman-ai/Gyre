# Score verification model

Gyre keeps three statements separate:

1. **A participant reported a score.**
2. **The score was reproduced from public code.**
3. **The method generalises beyond the public development cases.**

They are not interchangeable.

## Verification classes

```text
self-reported
    public claim + provenance receipt
    no independent rerun
    not eligible for verified ranking

public-reproducible
    implementation and scorer are public
    CI reruns the result
    eligible for the public-development ranking

sealed-evaluator-attested
    trusted evaluator controls hidden cases and execution
    signed public receipt
    eligible only after signature verification is implemented
```

The first class protects private machinery but cannot establish truth. The
second establishes reproducibility on visible cases but not resistance to
overfitting. The third can test a private system without publishing it, but
only if the evaluator controls the run and the attestation is verifiable.

## Public transparency

Every scoreboard row declares:

- `verification.class`;
- `verification.ranking_eligible`;
- `verification.evidence_scope`;
- a plain-language verification statement;
- a receipt path when a receipt exists;
- a public factory specification when CI must import a community contender.

The board remains one public record, but unverified claims never silently share
the epistemic status of reproduced results.

## Current limit

Gyre does not yet operate a sealed evaluator or signing key. Any private score
currently published is a self-report, including the maintainer's protected
development candidate. This is a deliberate falsifier of the project's own
temptation to treat a leading number as validated evidence.

See [Submitting a score](contributing-a-score.md) for exact commands.
