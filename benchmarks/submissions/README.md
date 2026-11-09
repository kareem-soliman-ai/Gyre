# Score submissions

This directory contains machine-readable score receipts, not private
implementations.

- A `public-reproducible` receipt names a public `module:factory`; CI imports it
  and reruns the score.
- A `self-reported` receipt omits the private factory path and is displayed only
  as an unverified claim. It is never eligible for the verified ranking.
- A future `sealed-evaluator-attested` receipt will be produced by a trusted
  evaluator on hidden cases. The public verifier deliberately rejects that
  class until signature verification exists.

Read [the contribution guide](../../docs/contributing-a-score.md) before adding
a receipt. JSON files in this directory are public. Do not include private
paths, prompts, model identifiers, credentials, or implementation details.

