# EXP-01 Protocol Deviations

## 2026-07-28 — StepFun reasoning control

The first `stepfun/step-3.7-flash` judgement exhausted three requests with empty
`content`. The generation and the first two blind judge receipts were retained.
No scores were imputed.

A live OpenRouter catalogue check showed that this model requires reasoning,
defaults to medium effort, supports low effort, and supports exclusion of the
reasoning trace. OpenRouter's official documentation states that reasoning
tokens count against output tokens. The retry therefore keeps the
preregistered 1,000-token output ceiling and model fixed but adds:

```json
{"reasoning": {"effort": "low", "exclude": true}}
```

This is an operational protocol deviation because the reasoning setting was not
frozen in the preregistration. It is intended to leave room for the requested
JSON answer, not to change the comparison prompt or scoring rubric. Results
must disclose the deviation.

## 2026-07-28 — Replacement blind judge

The low-reasoning retry also returned empty content on all three attempts.
`stepfun/step-3.7-flash` was therefore replaced with
`openai/gpt-5.4-mini`, a distinct model family available in the live OpenRouter
catalogue. The replacement retained the same blind assignments, task material,
rubric, temperature setting, and 1,000-token response ceiling.

The replacement model was selected after observing the StepFun failure and was
not preregistered or independently qualified on this rubric. The final panel
must be described as Gemma, DeepSeek, and GPT-5.4 Mini, and the result remains
qualification evidence rather than a confirmatory test.

## 2026-07-28 — Replacement-judge JSON enforcement

The third GPT-5.4 Mini judgement reached the 1,000-token ceiling with an
unterminated JSON object. Its blind assignment was retained and no score was
imputed. Subsequent retries add OpenRouter's supported
`{"response_format": {"type": "json_object"}}` request option while retaining
the same prompt, model, seed, and token ceiling.

The first two successful GPT-5.4 Mini receipts did not use this API-level JSON
enforcement. This within-judge request difference is another protocol
deviation. One truncated response and the failed StepFun calls did not retain
provider usage, so the final successful-receipt cost is a lower bound on total
API spend; the USD 0.50 stopping ceiling remains far above the conservative
maximum implied by these failed calls.
