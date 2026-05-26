# Governance

Polymer Claims is administered by Zachary Belden, MD ([@beldez01](https://github.com/beldez01)), with contributor tiers that progressively decentralize review. Transitions between governance phases fire on **observable triggers** (queue depth, time-to-merge, contributor-tier readiness), not calendar dates.

## Contributor tiers

| Tier | Name | Preconditions | Merge rights | Badge |
|---|---|---|---|---|
| 0 | Unverified | New GitHub login, no merged claims | None; every PR admin-reviewed | `tier-0` |
| 1 | Established | ≥5 merged claims AND 0 post-merge retractions in the last 180 days AND (linked ORCID OR ≥90-day-old GitHub account) | Auto-merge own LICENSED, non-contested claims in any domain | `tier-1` |
| 2 | Domain co-reviewer | Invited by admin; Tier-1 prerequisite; named in `domains/<d>/_domain.yml` with a commit co-signed by admin | Approve + merge LICENSED and PENDING claims in the named domain(s); cannot self-merge own PRs | `tier-2 · <domain>` |
| 3 | Federated admin | Invited by admin + existing Tier-2 status ≥6 months + ≥30 PRs approved without rollback | Full merge for a claim subspace; can invite Tier-1 contributors in that subspace | `tier-3 · <subspace>` |

All tiers are encoded authoritatively in `contributors/<github-login>.yml`. Auto-merge policy is in `tiers/policies.yml`.

### Demotion

A contributor is demoted one tier on any of:
- Two post-merge retractions in 90 days.
- One confirmed sybil ring, coordinated citation ring, or PHI leak.
- Manual admin override (committed to `contributors/<login>.yml` with rationale).

A demotion entry appears in the contributor's viewer profile for 180 days.

### Pseudonymous submitters

Allowed at Tier 0 and Tier 1 only. File your `contributors/<login>.yml` with `pseudonymous: true` and either `orcid: null` or an anonymous ORCID. Cap at Tier 1 until a verified identity links to the GitHub account.

## Governance phases

### Phase 0 — Solo admin (now → ~100 merged claims)

Admin reviews every PR. Admin time: ~5 min / LICENSED, ~20 min / PENDING, ~30 min / contested. At 5 PRs/week: ~2 h/week. Tolerable. Transition triggers below move us to Phase 1.

### Phase 1 — Tier-1 auto-merge unlocked (~100 → ~500)

LICENSED claims from Tier-1+ contributors auto-merge (see `tiers/policies.yml`). Admin reviews: (a) Tier-0 submissions, (b) PENDING, (c) contested, (d) adversarial-flagged.

### Phase 2 — Tier-2 domain co-reviewers (~500 → ~2000)

Invited collaborators hold Tier-2 merge rights for their domain: HLA co-reviewer, recombination / CNV co-reviewer, Bioconductor co-reviewer, etc. Admin becomes cross-domain arbiter.

### Phase 3 — Federated admins (~2000+)

Tier-3 federated admins own claim subspaces. Admin is final arbiter for cross-domain and contested claims only. Whether this becomes a DAO, a journal-adjacent editorial board, or remains foundation-adjacent is a downstream decision — the tier-3 merge-rights infrastructure supports either.

## Phase transitions are trigger-based

| Trigger | Fires transition |
|---|---|
| Admin queue depth >25 PRs / >7 days, sustained 14 days | Phase 0 → 1 |
| Median time-to-merge for LICENSED >5 business days | Phase 0 → 1 |
| ≥3 contributors meet Tier 1 AND admin time ≥10 h/week | Phase 0 → 1 |
| Any single domain >50 active claims with ≥2 qualified reviewers | Phase 1 → 2 (that domain) |
| Any Tier-2 reviewer hits Tier-3 criteria AND cross-domain queue >10 | Phase 2 → 3 |

Meeting a trigger is not automatic promotion — the admin still signs the commit — but triggers make the decision legible to contributors and funders ("here is the criterion; here is the current metric").

## SLAs

- Tier-0 LICENSED: merge within **5 business days**
- PENDING: admin decision within **10 business days**; auto-escalation issue filed at day 7
- REJECTED feedback: machine-readable diagnostic posted by CI within **5 minutes** of push

## Adversarial protections

1. **Schema + content hash** on every submission.
2. **Evaluator verdict** as a required CI gate — LICENSED requires real conjunct evaluation, not rubber-stamp.
3. **GitHub identity** on every commit.
4. **Rate limits per tier** (Tier-0: 3 open + 5 merged / 7d; Tier-1: 10 + 25; Tier-2+: 100 / week).
5. **PHI heuristic** scans `claim.text` + `notes` for DOB / MRN patterns → forced PENDING.
6. **Corpus-rebuild scans** for adversarial patterns:
   - Dense citation subgraphs (contributors only citing each other).
   - Claims with empty `mcp_invocations` but a statistical effect claim.
   - Contributor's last 20 claims all positive (publication-bias flag).
7. **Post-merge flagging** via issue template. Retractions are new PRs with `verdict: RETRACTED`. Downstream claims get an `UPSTREAM_RETRACTED` warning.

## Dispute and supersession

When a new claim declares `relations.contradicts: [X]`:
1. The evaluator flags `DISPUTE_DECLARED` in its CI payload.
2. On merge, the viewer renders both claims in a side-by-side dispute card.
3. A `dispute` GitHub issue auto-opens tagging the domain reviewers.

Admin (or Tier-2+ for in-domain disputes) adjudicates one of:
- **Both stand** — merge with `coexists_with` relation.
- **One supersedes** — the surviving claim gets `relations.supersedes: [X]`; the superseded one gets `verdict: SUPERSEDED`; both remain queryable for provenance.
- **Both retracted** — rare; admin co-signs retractions on both.

Resolution is itself filed as a machine-queryable claim (`claim_type: dispute_resolution`).

## Contact

- Admin: [@beldez01](https://github.com/beldez01)
- Public: [@polymergenomics](https://x.com/polymergenomics)
- Discussion: [GitHub Discussions](https://github.com/beldez01/polymer-claims/discussions)
