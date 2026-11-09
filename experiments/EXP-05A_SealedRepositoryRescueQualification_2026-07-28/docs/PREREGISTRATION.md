# EXP-05A Sealed Repository Rescue Scorer Qualification

## Objective

Build the first executable scorer for Gyre's Sealed Repository Rescue task
before evaluating a preferred human-system controller.

The qualification question is:

> Does the scorer accept more than one correct event-reconciliation
> implementation, reject declared defect families, preserve the published
> category weights, and remain deterministic across development seeds?

This is an engineering qualification, not yet a fair public benchmark. The
three-independent-reviewer screen, clean-container parity check, and genuinely
sealed post-freeze generator remain required.

## Methodology

### Frozen task contract

The candidate exposes:

```python
reconcile(events, checkpoint=None) -> state
```

Each event has a non-empty `id`, non-negative integer `sequence`, non-empty
`key`, and one of:

- `set`, with a `value`;
- `increment`, with a finite numeric `value`;
- `delete`.

The candidate must:

1. validate the complete incoming batch before applying it;
2. apply events in `(sequence, id)` order;
3. ignore exact duplicate ids;
4. reject conflicting duplicate ids;
5. preserve a replayable checkpoint;
6. reject an unseen event at or before the checkpoint frontier;
7. be idempotent when events are replayed;
8. return `values`, ordered `applied_ids`, canonical `seen` events,
   `last_sequence`, and a deterministic summary;
9. leave inputs unchanged.

### Frozen score

| Category | Points |
|---|---:|
| Behavioural conformance | 55 |
| Regression preservation | 15 |
| Robustness and metamorphic behaviour | 15 |
| Recovery, replay, and idempotency | 10 |
| Performance boundary | 5 |

The score is the weighted proportion of cases passed in each category. A
correct implementation can take any internal form.

### Qualification cells

- executable reference model;
- structurally separate correct implementation;
- intentionally broken starter;
- order, duplicate, checkpoint, and summary defect variants;
- three deterministic development seeds: 419, 919, and 1429.

### Gates

The engineering gate passes only if:

1. reference and alternate-correct implementations score 100 on every seed;
2. every declared invalid variant scores below 100;
3. identical repeated runs produce identical category scores;
4. every category has at least one test;
5. no result is represented as independent fairness or joint-capability
   evidence.

The public-benchmark gate remains closed until three independent reviewers,
container parity, hidden-seed sealing, and anti-tamper review are complete.

## Results

Populated after execution in `../results/`.

## Discussion

Reserved until execution.

## Next Steps

If the engineering gate passes, run a single measured-control mechanics pilot
on untouched development seeds. Do not estimate joint-capability gain until
matched human-only, system-only, and ordinary-chat conditions exist.

