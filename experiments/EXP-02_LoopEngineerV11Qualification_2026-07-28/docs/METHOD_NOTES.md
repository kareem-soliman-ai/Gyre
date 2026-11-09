# EXP-02 Method Notes

These sources informed the redesign but are not evidence for Gyre's result.

- [On Randomness in Agentic Evals](https://arxiv.org/abs/2602.07150) reports
  material single-run variation in agent evaluations and recommends repeated
  independent trials and reliability-aware metrics. EXP-02 therefore crosses
  two seeds with every task, model, and arm and reports whether both runs pass.
- [SWE-bench](https://arxiv.org/abs/2310.06770) demonstrates the value of
  realistic tasks with executable acceptance tests. EXP-02 moves its primary
  endpoint from mention-level scoring to public-validator plus task-specific
  contract checks. It still stops short of implementation-bearing repository
  work.
- [Judging LLM-as-a-Judge with MT-Bench and Chatbot
  Arena](https://proceedings.neurips.cc/paper_files/paper/2023/file/91f18a1287b398d378ef22505bf41832-Paper-Datasets_and_Benchmarks.pdf)
  documents position and verbosity biases in model judges. EXP-02 keeps
  deterministic checks primary, swaps A/B order, and counts only consistent
  underlying preferences.
- [AstaBench](https://arxiv.org/abs/2510.21652) emphasizes controlled,
  reproducible tool interfaces and comprehensive baselines for scientific
  agents. EXP-02 matches repair feedback and budgets across arms and includes
  both a bare and a strong template baseline.
- [OpenAI's model-selection
  guidance](https://developers.openai.com/api/docs/guides/latest-model)
  recommends representative evaluations and removing instruction groups to
  identify what contributes value. The template-only ablation isolates the
  marginal contribution of the v1.1 instructions from the JSON scaffold.

These methodological analogies do not make EXP-02 confirmatory science. The
task bank, checks, and skill were authored in the same project, two replicates
are sparse, and no human developer implements the proposed contracts.
