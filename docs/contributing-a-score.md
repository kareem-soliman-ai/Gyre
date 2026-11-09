# Submitting a score

A Gyre score can be public while the machinery that produced it stays private.
What cannot remain hidden is the **verification status**.

## Choose a track

| Track | What you publish | What Gyre can verify | Verified ranking? |
|---|---|---|---|
| Public reproducible | Code, factory specification, score receipt | CI reruns the exact public scorer | Yes |
| Private self-report | Score receipt only | Receipt shape and scorer provenance, not the score | No |
| Sealed evaluator | Private runnable submitted to a trusted evaluator, public signed receipt | Evaluator reruns hidden cases | Yes, once the public attestation verifier exists |

Gyre currently implements the first two tracks. The sealed evaluator is a
specified next step, not a capability the repository pretends to have.

## Public reproducible submission

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR-USERNAME/Gyre.git
cd Gyre
git remote add upstream https://github.com/kareem-soliman-ai/Gyre.git
git checkout -b sensor/my-clever-detector

# Add contenders/my_detector.py with a zero-argument build() factory.
python scripts/challenge.py \
  --contender contenders.my_detector:build \
  --write-receipt benchmarks/submissions/YOUR_HANDLE-my-detector.json \
  --submitter YOUR_HANDLE \
  --update-scoreboard

# Verify exactly what CI will verify.
python scripts/verify_score_receipts.py
python scripts/verify_scoreboard.py
python -m pytest -q

git add contenders/my_detector.py \
  benchmarks/submissions/YOUR_HANDLE-my-detector.json \
  docs/scoreboard.json
git commit -m "feat(sensor): add my detector"
git push origin sensor/my-clever-detector
gh pr create --fill
```

`--update-scoreboard` upserts the scored provider. It does not trust a manually
typed number. CI imports the recorded `module:factory`, regenerates the receipt
score, and recomputes the scoreboard row.

## Private self-reported submission

The safest arrangement is to keep the implementation in a separate private
checkout and install it into the same Python environment:

```bash
python -m pip install -e C:\path\to\your-private-sensor

python scripts/challenge.py \
  --contender your_private_package.sensor:build \
  --visibility private \
  --write-receipt benchmarks/submissions/YOUR_HANDLE-private-sensor.json \
  --submitter YOUR_HANDLE \
  --update-scoreboard
```

Alternatively, work under `contenders/private/`. That directory is gitignored:

```bash
python scripts/challenge.py \
  --contender contenders.private.my_sensor:build \
  --visibility private \
  --write-receipt benchmarks/submissions/YOUR_HANDLE-private-sensor.json \
  --submitter YOUR_HANDLE \
  --update-scoreboard

git check-ignore -v contenders/private/my_sensor.py
git status --short
```

Inspect the receipt before committing it. A private receipt contains the
provider's public name and scores but sets `implementation.factory` to `null`;
it does not publish the module path. It is labelled `self-reported`,
`ranking_eligible: false`, and appears outside the verified ranking.

Only add the receipt and scoreboard row:

```bash
git add benchmarks/submissions/YOUR_HANDLE-private-sensor.json docs/scoreboard.json
git diff --cached
```

Never use `git add -f` on private machinery. If `git status --short` shows a
private file, stop before committing and add its path to your own
`.git/info/exclude`:

```text
# .git/info/exclude stays local to your clone
/my-private-work/
/scripts/my-local-evaluator.py
```

Use `.git/info/exclude` for personal paths that should not change the shared
`.gitignore`.

## What a receipt proves

A receipt binds a claim to:

- provider name and per-corpus/per-cell metrics;
- UTC time, Python/platform information, and Git revision/dirty state;
- SHA-256 hashes of the public scorer, benchmark harness, and corpus generator;
- implementation visibility and verification class.

That proves which public test definition the claimant says they used. It does
**not** prove a private system actually produced the number.

## What independent private verification requires

A credible sealed track needs all of the following:

1. A versioned hidden benchmark season whose cases and labels are sealed.
2. A private container or endpoint supplied to a trusted evaluator.
3. Predictions committed before labels or aggregate results are revealed.
4. A public signed receipt containing evaluator identity, benchmark hash,
   scorer hash, case count, metrics, output hash, execution ID, and timestamp.
5. A public verifier for the evaluator signature.
6. Retirement and later release of old hidden suites where licensing permits,
   so the community can audit the evaluation retrospectively.

An endpoint alone is insufficient: it could recognise public cases or change
between calls. A hash alone is insufficient: it proves file identity, not that
the file was executed. The evaluator must control the cases and the run.

## What CI checks

`.github/workflows/scoreboard.yml` uses the safe `pull_request` event with a
read-only token and no repository secrets. It runs:

| Gate | Question |
|---|---|
| `pytest` | Does the repository still work? |
| claims gates | Do public claims remain tied to reproducible evidence? |
| `verify_scoreboard.py` | Does every ranking-eligible row rerun, and are self-reports excluded? |
| `verify_score_receipts.py` | Do public receipts reproduce, and are private receipts visibly labelled `UNVERIFIED`? |

Do not change this workflow to `pull_request_target` to access secrets. That
would execute untrusted pull-request code with base-repository privileges.

## Interpreting a win

The current cases are public, deterministic synthetic development cases. A
participant can overfit them. A higher pooled score is therefore a result on
this benchmark version, not evidence of general validity.

Inspect trap-cell performance, method-family independence, sealed holdouts, and
transfer to appropriate real traces before making a stronger claim.
