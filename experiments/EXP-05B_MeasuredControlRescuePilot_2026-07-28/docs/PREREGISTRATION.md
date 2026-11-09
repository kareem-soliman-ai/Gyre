# EXP-05B Measured-Control Rescue Mechanics Pilot

## Objective

Run one complete measurement-control-submit cycle against the EXP-05A
event-reconciliation scorer and report the Verified Outcome Score separately
from resource use and controller-promotion status.

This run asks whether the machinery works end to end. It cannot estimate joint
capability gain because matched human-only, system-only, and ordinary-chat
baselines have not yet been run.

## Methodology

- Candidate implementation is frozen in `scripts/submission.py`.
- Prospective forecasts are frozen in `prospective-forecast.json`.
- Final development seeds are 2909, 3251, and 4001.
- No validation probe is used before final scoring.
- The score is the mean 0-100 Verified Outcome Score across seeds.
- Efficiency is reported as a vector: wall time, scorer calls, validation
  probes, active human minutes, and API cost. Missing quantities remain
  missing; they are not replaced with zero.
- The outcome-reliability sensor records only resolved verifier outcomes.
- The promotion gate receives a synthetic, self-evaluated receipt and is
  expected to block autonomous controller promotion.

## Results

Populated after execution in `../results/`.

## Discussion

Reserved until execution.

## Next Steps

Run matched constituent and ordinary-chat baselines on newly generated sealed
instances before calculating joint-capability gain.
