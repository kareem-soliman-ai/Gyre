# NotebookLM production notes

Create one NotebookLM notebook per source pack in
[`SOURCE_MANIFEST.md`](SOURCE_MANIFEST.md). Upload the listed canonical files
directly from the repository; do not copy them into this folder and create a
second source of truth.

For each generated script:

1. Ask NotebookLM to cite the source file for every factual claim.
2. Remove claims that exceed the repository's stated evidence boundary.
3. Keep objective outcome, human acceptance, and implementation status
   separate.
4. Export a draft, then reconcile it against the hand-authored production
   script under `videos/explainers/`.
5. Preserve failed experiments and open gates. They are part of the lesson.

Suggested house prompt:

> Explain this for a technically curious developer without assuming control
> theory. Distinguish observation, measurement, controller, action, and
> independent outcome. State what the experiments demonstrated, what failed,
> and what remains unverified. Use the Alien Factory as a concrete example and
> do not infer proprietary implementation details.

