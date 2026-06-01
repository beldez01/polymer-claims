---
name: submit-claim
description: Use after /validate-claim returned LICENSED. Forks beldez01/polymer-claims under the user's GitHub account, writes the claim to the right domain directory, and opens a PR using the repo's template. Requires the user's own `gh` CLI to be authenticated; never handles credentials.
---

# Submit a FormalClaim

This skill takes a locally-validated claim file and opens a PR on `github.com/beldez01/polymer-claims`.

## Preconditions

- `/validate-claim` returned **LICENSED**. If not, refuse and tell the user to fix the REJECTED / PENDING issues first.
- `gh` CLI is installed and authenticated as the user (`gh auth status`).
- The claim's `domain` + target topic directory are unambiguous (agent picks from the subject kind / title; asks if ambiguous).

## What it does

Runs `./scripts/open-pr.sh <claim-path>` which:

1. Validates the claim one more time (belt-and-suspenders).
2. Computes a short slug from the claim title (or accepts `--slug`).
3. Picks the target `corpus/domains/<topic>/` based on subject kind:
   - `genomic_region` + HLA in scope → `hla`
   - `genomic_region` otherwise → `recombination_hotspots`, `te_surveillance`, or `dual_channel` (agent asks if unclear)
   - `gene_or_protein` → transcriptomic-leaning → `dual_channel` by default
   - Clinical → `methylation` (today) / dedicated clinical topic once one exists
4. Forks `beldez01/polymer-claims` to the user's account if not already forked.
5. Creates a new branch `submit/<slug>/<shorthash>`.
6. Writes `corpus/domains/<topic>/claims/<slug>.json`.
7. Opens a PR with the repo's PR template pre-filled (local evaluator output, agent identity, human contributor, relations).

## Credential boundary

- **We never touch user credentials.** The script uses the user's authenticated `gh` CLI; all tokens remain in the OS keychain managed by `gh`.
- If `gh auth status` fails, refuse with instructions to run `gh auth login`.
- The submission is on the user's own GitHub identity. They own the PR.

## Output

On success, the skill prints the PR URL and the expected CI timeline:

```
✓ PR opened: https://github.com/beldez01/polymer-claims/pull/<N>
  status-check "evaluator/verdict" will complete within ~90 seconds.
  label: admin-review:<licensed|pending|rejected> (from CI)
  tier: <your tier>  → auto-merge: <yes/no>
```

## Iteration after submission

If CI re-evaluates to REJECTED (it should not, you ran the same evaluator locally — but schema versions may have bumped), call `/validate-claim` with the machine-readable feedback JSON and iterate. Push to the same branch; the sticky comment updates.
