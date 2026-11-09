# EXP-05A Sealed Repository Rescue Scorer Qualification

## Objective

Determine whether the first event-reconciliation scorer is mechanically
sensitive to declared defects while accepting multiple correct
implementations.

## Methodology

The frozen scorer was run on development seeds 419, 919, and 1429 against:

- the executable reference model;
- a separately written dictionary-reduction implementation;
- an intentionally order-dependent starter;
- a wrong-summary mutant;
- a checkpoint-ignoring mutant;
- an input-order mutant.

The scorer used the preregistered 55/15/15/10/5 category weights.

## Results

All scores were identical across the three development seeds.

| Implementation | Score | Interpretation |
|---|---:|---|
| Reference | 100.00 | Accepted |
| Alternate correct | 100.00 | Accepted |
| Broken starter | 30.36 | Rejected |
| Wrong summary | 21.48 | Rejected |
| Ignores checkpoint | 92.50 | Rejected, with loss isolated to recovery |
| Applies input order | 30.36 | Rejected |

The engineering gate passed. The most informative cell was the
checkpoint-ignoring mutant: it retained 92.5 points while losing 7.5 of the 10
recovery points. This demonstrates progressive scoring rather than an
all-or-nothing test.

The public-benchmark gate did not pass. Outstanding requirements are:

- three independent fairness reviewers;
- clean-container parity;
- genuinely sealed post-freeze seeds;
- anti-tamper review.

## Discussion

The scorer can distinguish several intended defect families and does not force
one source-code solution. It has not yet demonstrated ecological difficulty or
fairness. Identical scores across seeds suggest that the current random cases
vary values more than structure, so this version is suitable for a mechanics
pilot but not yet a competitive leaderboard.

## Next Steps

Add structurally generated defect interactions, qualify the scorer in a clean
container, and obtain independent underspecification review before treating a
score as public benchmark evidence.

