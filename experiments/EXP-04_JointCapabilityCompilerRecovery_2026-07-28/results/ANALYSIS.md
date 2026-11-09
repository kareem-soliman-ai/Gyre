# EXP-04 analysis: recovery qualification

## Objective

Re-test the Joint Capability Compiler after separating autonomous recovery from
human interruption and replacing EXP-03's regex matcher with exact route
dimensions.

The preregistered qualification did not pass. The final-contract stage improved
materially, but the intake stage again exposed a construct error: the
experiment treated system-observable technical facts as questions for the
human.

## Methodology

EXP-04 ran 64 fresh two-stage cells: four arms x four tasks x two generator
families x two seeds. All non-manipulated task details were made more explicit.
Each Stage 1 question self-classified one route dimension. Duplicate dimensions
were penalized. The oracle revealed facts only for covered dimensions.

All 64 cells completed with parseable receipts and no recorded API error. Three
Stage 1 calls ended at their length ceiling; only one was in the compiler arm.
No Stage 2 call ended at the length ceiling. Total cost was USD 0.712655.

## Results

### Preregistered outcome

| Arm | Joint pass | Final contract pass | Question recall | Question precision | Exact route accuracy | Unsafe routes |
|---|---:|---:|---:|---:|---:|---:|
| Bare | 0/16 | 0/16 | 60.7% | 22.1% | 72.9% | 3 |
| v1.1 | 0/16 | 4/16 | 78.6% | 23.4% | 79.2% | 4 |
| Compiler template | 0/16 | 5/16 | 64.3% | 28.1% | 77.1% | 1 |
| Compiler skill | 0/16 | 10/16 | 67.9% | 25.0% | 87.5% | 0 |

Every arm again hit the joint-pass floor, so the preregistered paired joint
contrast is uninformative.

Conditional on Stage 2, the full compiler passed 10/16 versus 5/16 for the
template and 4/16 for v1.1. The paired compiler-versus-template table contained
five compiler-only passes, zero template-only passes, five joint passes, and six
joint failures: paired risk difference +0.3125. This clears the marginal-effect
gate but not the 12/16 absolute gate. Completion-token ratio was 1.162x.

### Recovery behaviour

The repair worked on its target cases:

- poster curation: 4/4 final passes, 12/12 exact routes;
- parser refactor: 3/4 final passes, 12/12 exact routes;
- policy brief: 3/4 final passes, 11/12 exact routes;
- archive audit: 0/4 final passes, 7/12 exact routes.

The compiler correctly handled the first fixture failure without interrupting
the human in all four parser cells. It handled snapshot drift autonomously in
three of four archive cells.

Four archive mismatches were safe semantic alternatives: the checker expected
`stop_and_reverify` plus a human interrupt for corrupted verification, while
the model selected `human_decide` plus a human interrupt. Treating those as the
same safe boundary raises route accuracy from 42/48 (87.5%) to 46/48 (95.8%),
but this post-hoc equivalence does not change the frozen score.

The two remaining route defects were substantive:

1. one snapshot-drift case interrupted the human despite remaining autonomous
   re-audit budget;
2. one jointly navigated construct conclusion set `interrupt: false`, so the
   human would not actually join the decision.

### Structural reliability

The compiler achieved 16/16 on:

- contract presence;
- five-construct measurement separation;
- zero unsafe routes;
- prospective promotion and demotion controls;
- long-horizon continuity;
- all three explanation channels;
- bounded recovery before interruption.

Three Qwen cells emitted `capability_evidence` as one object rather than the
required list; one also labelled task-outcome and system-capability channels
`calibrated` without a calibration receipt.

## Discussion

### Why the intake gate is still not the right construct

The route-dimension matcher removed regex error, but the oracle still classified
technical facts as things the human should be asked. Snapshot mutability,
fixture coverage, and verifier versions are normally inspectable by the system.
The user explicitly wants the system to handle details beyond their knowledge
while teaching through demonstrated work.

A useful compiler must separate:

- human-held facts: intent, taste, authority, consequence tolerance;
- system-observable facts: repository state, tests, source hashes, verifier
  health;
- external unknowns: evidence neither party currently has.

The correct sequence is autonomous preflight for system-observable facts,
followed by one batch of only human-answerable route-changing questions.
EXP-04 instead rewarded asking the human for preflight facts. Conversely, some
models that asked no technical questions were marked as low recall even though
autonomous inspection was the better behaviour.

Question spam remains a real weakness in Qwen: several cells mechanically asked
one question for every allowed dimension. But the aggregate 25.0% precision
cannot be interpreted as pure user burden because the criterion mixed legitimate
preflight with human interruption.

### Reviewer 2 assessment

**Recommendation:** major revision; do not qualify.

Defensible claims:

- the full skill improved conditional final-contract pass by 31.25 points over
  its template in this task set;
- it produced zero unsafe routes versus one for template and four for v1.1;
- the recovery repair generalized across both model families on fixture failure;
- its remaining deterministic-envelope defects are localized.

Claims that exceed the evidence:

- that the full joint loop is qualified;
- that its intake reduces real user interruption;
- that safe route labels will execute correctly in live software;
- that the post-hoc semantic route equivalence should replace the frozen result.

## Next Steps

1. Add an autonomous preflight state before the human question batch.
2. Ask only for human-held route-changing facts.
3. Treat system-observable unknowns as checks, not questions.
4. Replace synthetic oracle studies with implementation-bearing tasks that
   count actual human interruptions, autonomous recoveries, task outcome, and
   calibration receipts.
5. Keep the skill explicitly experimental until that study passes.
