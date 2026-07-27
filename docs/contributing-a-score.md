# Submitting a sensor to the scoreboard

Yes, this works, and the mechanism is worth understanding because it is the same
epistemics the rest of the repo runs on: **your number is not accepted because
you reported it. It is accepted because CI recomputes it and gets the same
answer.** You cannot inflate a score, and we cannot quietly leave a stale one in
place.

---

## The short version

```bash
# 1. Fork on GitHub (button, top right), then:
git clone https://github.com/YOUR-USERNAME/Gyre.git
cd Gyre
git remote add upstream https://github.com/kareem-soliman-ai/Gyre.git

# 2. Branch
git checkout -b sensor/my-clever-detector

# 3. Add your sensor under contenders/ and score it
python scripts/challenge.py --contender contenders.my_detector:build

# 4. Regenerate the board (never hand-edit it)
python scripts/challenge.py --rebuild-scoreboard

# 5. Commit and push
git add contenders/my_detector.py docs/scoreboard.json
git commit -m "Add my-clever-detector to the scoreboard"
git push origin sensor/my-clever-detector

# 6. Open the PR (GitHub prints a link, or use the CLI)
gh pr create --fill
```

CI then re-runs the bench on your sensor and diffs its own result against the
file you committed. If they disagree, the PR goes red with the exact metric and
the size of the discrepancy.

---

## What each step is actually doing

**Fork.** A fork is your own copy of the repository under your account. You have
write access to it; you do not have write access to ours. This is what makes
open contribution safe in both directions.

**`upstream`.** Your fork does not automatically track our changes. Adding a
remote called `upstream` lets you pull them later:

```bash
git fetch upstream
git rebase upstream/main      # replay your work on top of the latest main
```

Rebase rather than merge, so your branch stays a clean sequence of your own
commits rather than a tangle of merge commits.

**Branch.** Never work on `main` in a fork you intend to PR from. One branch per
contribution keeps your submissions independent, so a problem with one does not
block another.

**Regenerate, do not edit.** `docs/scoreboard.json` is generated output. Editing
it by hand is exactly the failure mode the CI check exists to catch, and it will
be caught.

**Pull request.** A PR is a request for us to merge your branch, plus a place to
discuss it. Pushing more commits to the same branch updates the PR
automatically, so review feedback does not mean starting over.

---

## What CI checks, and why it is built this way

`.github/workflows/scoreboard.yml` runs four gates:

| Gate | Question |
|---|---|
| `pytest` | Does the repo still work? |
| `check_claims.py` | Is every public claim tagged to a ledger entry? |
| `verify_claims_evidence.py` | Do the claimed figures still reproduce? |
| `verify_scoreboard.py` | Does the committed board match a fresh recomputation? |

**One security detail worth knowing if you ever build something like this.** The
workflow triggers on `pull_request`, not `pull_request_target`. That distinction
matters enormously: `pull_request` runs a fork's code with a **read-only token
and no access to repository secrets**, which is the only sane posture when the
job's entire purpose is to execute code a stranger wrote.
`pull_request_target` runs with write permissions against the base repo, and
using it to run untrusted code is one of the best-known ways to hand your
repository to whoever opens a PR. If you see a tutorial recommending it "so
secrets work", that tutorial is teaching you to build a vulnerability.

The consequence for you: CI here needs no API keys, because the public tier is
stdlib-only and every corpus is generated deterministically from code in the
repo. That is not an accident of packaging; it is what makes open verification
possible at all.

---

## What makes a submission interesting

Not a higher pooled number. The board shows per-cell results because a pooled
win that loses the trap cells is measuring surface form, and we would rather
merge an honest 0.7 that holds the traps than a 0.9 that does not.

Genuinely interesting submissions:

- A sensor that **beats `psy:evi-semantic` while holding the trap cells.** That is
  a real finding about the construct, and we will say so loudly.
- A sensor built on a **different method family** to everything on the board.
  Convergent validity needs independent instruments, so a new method is worth
  more than an incremental tune of an existing one.
- A **falsification**: a case where the published ordering does not hold. Open an
  issue with your `--json` output. This repository's own record includes results
  that went against it, and one more would be welcome.

---

## If you do not want to submit anything

You do not have to. Run `python scripts/challenge.py` against your own sensors
locally and never tell us the result. The board exists so you have something to
beat, not so we can collect telemetry: nothing in this repo phones home, and
the only way we learn your score is if you choose to open a PR.
