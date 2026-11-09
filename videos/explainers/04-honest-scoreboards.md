# Explainer 04: An honest scoreboard

**Target:** 2.5 minutes. **Outcome:** the viewer understands all trust classes.

Narration:

> A number in JSON is a claim. It becomes reproducible only when someone else
> can rerun the same scorer on the same implementation and cases.

Visual: three columns labelled `self-reported`, `public-reproducible`, and
`sealed-evaluator-attested`.

> Public contenders publish a factory specification. Gyre's CI imports the code,
> regenerates the score, and fails the pull request if any metric disagrees.

> Private contenders can keep their machinery outside the repository and
> publish a receipt. The receipt records hashes, environment, benchmark scope,
> and the score, but it deliberately omits the private module path. That protects
> the implementation. It does not verify the result. The row is labelled
> self-reported and excluded from the verified ranking.

> A future sealed evaluator can run private code against hidden cases and emit a
> signed public receipt. Until the evaluator controls the run and signatures can
> be checked, Gyre will not use that label.

Close:

> Transparency does not require pretending everything is equally known. It
> requires making the boundary visible.

Demo:

```text
python scripts/verify_score_receipts.py
python scripts/verify_scoreboard.py
```

