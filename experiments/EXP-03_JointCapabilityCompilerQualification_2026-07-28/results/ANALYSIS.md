# EXP-03 analysis: Joint Capability Compiler

## Objective

Test whether the experimental compiler improves the chain from one upfront
question batch to capability-aware runtime routing. The preregistered
qualification did not pass. More importantly, the primary joint-pass measure
was not a valid adjudicator because the hidden critical-question set was
incomplete.

## Methodology

The frozen study ran 64 two-stage cells: four arms x four tasks x two generator
families x two seeds. A regex matcher decided which hidden facts the answer
oracle revealed. Final envelopes were scored deterministically on runtime
routes, five-construct separation, capability updating, continuity, and output
channels.

All 64 cells returned stage receipts with parseable JSON and no recorded API
error. Two of 64 Stage 1 responses and eight of 64 Stage 2 responses ended at
the configured length ceiling. Candidate and template each had four Stage 2
length finishes. Total successful-receipt cost was USD 0.821995.

## Results

### Preregistered outcome

| Arm | Joint pass | Final contract pass | Question recall | Question precision | Route accuracy | Unsafe routes |
|---|---:|---:|---:|---:|---:|---:|
| Bare | 0/16 | 2/16 | 32.1% | 9.3% | 68.8% | 0 |
| v1.1 | 0/16 | 2/16 | 50.0% | 23.2% | 70.8% | 2 |
| Compiler template | 0/16 | 3/16 | 35.7% | 26.4% | 70.8% | 0 |
| Compiler skill | 0/16 | 5/16 | 42.9% | 26.1% | 70.8% | 0 |

Every arm hit the floor on joint pass. The candidate-versus-template joint-pass
risk difference was therefore 0.000, exact McNemar p = 1.000, with an
uninformative [0, 0] bootstrap interval.

Conditional on the flawed intake/oracle stage, the compiler produced two
additional final-contract passes and no template-only passes: 5/16 versus 3/16,
a paired risk difference of +0.125. This is descriptive, not qualification
evidence.

### Candidate failure localization

The candidate separated all five constructs in 16/16 cells and produced no
unsafe runtime route. Its dominant defect was exact runtime control:

| Task | Final passes | Exact runtime routing |
|---|---:|---:|
| Low-consequence identity exploration | 4/4 | 100.0% |
| Reversible pipeline migration | 0/4 | 66.7% |
| Consequential research release | 1/4 | 66.7% |
| Week-long corpus audit | 0/4 | 50.0% |

Ten of 16 candidate cells failed exact runtime routing. In all four pipeline
cells, the system correctly stopped on fixture failure but unnecessarily
interrupted the human. In all four week-long cells, source drift was escalated
to the human rather than handled through bounded autonomous revalidation. This
is not unsafe autonomy; it is excessive interruption and failure to distinguish
a control-flow pause from a human decision.

Other candidate failure counts were: decision-local capability evidence 4/16,
three output channels 3/16, and one failure each for contract presence, maturity
claims, promotion/demotion controls, and continuity.

## Discussion

### Critical methodology failure

The initial briefs omitted obvious route-changing facts that were absent from
the preregistered critical-question set. Examples include:

- the actual emerging research claim;
- the corpus and inclusion boundary;
- the audit criterion;
- the pipeline target stack;
- delivery and stopping boundaries.

Models that correctly asked these questions were scored as imprecise. The
oracle then withheld the answers. In one candidate cell, the compiler correctly
returned `needs_input` instead of manufacturing a contract because the research
claim and outcome criterion remained unknown; the checker counted this as a
contract failure.

The frozen regex patterns also missed clear paraphrases such as “Should the
final recommendation require explicit approval?” for final curation. Changing
patterns post hoc would invalidate the preregistration, so primary scores remain
unchanged. The appropriate conclusion is that EXP-03 cannot qualify or
disqualify the compiler's intake mechanism.

### What remains informative

The final-contract checks show a reproducible controller defect: the compiler
is conservative in a way that increases human disturbance. It knows when work
must stop, but does not reliably ask whether the system can repair verification
autonomously before involving the user.

The safe finding is therefore narrower than the hoped-for claim:

> Candidate C reliably separated measurement constructs and avoided unsafe
> autonomy in this study, but it did not yet compile low-interruption recovery
> policy reliably.

### Reviewer 2 assessment

**Recommendation:** reject EXP-03 as a qualification study; retain it as a
diagnostic pilot.

Strengths:

1. four-arm separation exposed template and historical-baseline effects;
2. exact task probes localized a consistent over-interruption failure;
3. every receipt, truncation, cost, and frozen score was retained.

Weaknesses:

1. incomplete hidden truth made question precision and recall criterion-invalid;
2. the all-arm joint-pass floor made the primary contrast uninformative;
3. oracle revelation depended on that flawed matcher, contaminating final-stage
   comparability;
4. synthetic envelopes still do not prove implementation quality.

Claims that exceed the evidence:

- that the compiler asks too many unnecessary questions;
- that its joint capability policy is worse than the template;
- that a 12.5-point conditional final-pass gain will transfer to live agents.

## Next Steps

1. Separate `stop_and_reverify` from `interrupt_human` in the skill and contract.
2. Fully specify every non-manipulated task fact in the next evaluation.
3. Replace regex semantic matching with an explicit route-dimension field.
4. Use a fresh task set and preserve EXP-03 as a failed measurement receipt.
5. Run implementation-bearing long-horizon tests only after the structural gate
   passes.
