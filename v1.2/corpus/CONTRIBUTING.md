# Contributing

Polymer Claims accepts contributions as **pull requests**. Claims are authored by an AI agent running in your own Claude Code session against the [Polymer Claims harness](https://github.com/beldez01/polymer-claims); CI validates every PR with the evaluator; trusted contributors' LICENSED claims auto-merge.

## 1. Install the harness

```bash
claude /plugin marketplace add beldez01/polymer-claims
claude /plugin install claim-harness@polymer-claims
```

This provides MCP servers (Polymer Genomics + BioContextAI + bio-mcp), the FormalClaim IR schema, the evaluator CLI, and the `author-claim` / `validate-claim` / `submit-claim` skills.

## 2. Author a claim

```
/author-claim "Do LINE-1 TEs in H3K9me3-enriched regions show lower ΔG37 variance than expected under GC null?"
```

The agent:
1. Searches the existing corpus for nearest related claims.
2. Picks a subject-slot template matching your question (TE family / gene / region / HLA allele / variant / pathway / cohort / clinical).
3. Calls MCP tools to build your premises, operations, statistics.
4. Writes a draft to `./claims/drafts/<slug>.json`.

## 3. Validate locally

```
/validate-claim ./claims/drafts/<slug>.json
```

You get one of three outcomes:

| Verdict | Meaning | Next step |
|---|---|---|
| **LICENSED** | Every inference conjunct evaluated true against pinned stats | Submit |
| **REJECTED** | At least one conjunct is false — claim is falsified | Either accept it as a null-result claim (set `claim_type: null_result`), revise the threshold with justification, or drop it |
| **PENDING** | Three-valued logic returned `null` (missing stats, unresolved ontology term, etc.) | Fix what's missing; the evaluator payload tells you which field |

Your harness's agent will iterate up to 3 rounds on machine-fixable REJECTED/PENDING reasons before paging you.

## 4. Submit

```
/submit-claim ./claims/drafts/<slug>.json
```

This:
- Forks this repo under your GitHub account.
- Writes `domains/<topic>/claims/<slug>.json` on a new branch.
- Opens a PR using the template.

## 5. CI + review

- **Evaluator CI** re-runs the evaluator on your PR. The verdict sets a required status check and a label (`admin-review:licensed` / `admin-review:pending` / `admin-review:rejected`).
- **LICENSED** + Tier-1+ contributor → auto-merged within minutes.
- **LICENSED** + Tier-0 → admin-reviewed within 5 business days.
- **PENDING** → admin review within 10 business days.
- **REJECTED** → PR stays open; machine-readable diagnostic posted as a comment; agent iterates.

## 6. Tiers

See `GOVERNANCE.md` for the full tier ladder. Short version:

| Tier | Preconditions | Merge rights |
|---|---|---|
| 0 | New GitHub login | None; admin reviews every PR |
| 1 | ≥5 merged claims, 0 retractions / 180d, ORCID or 90-day-old account | Auto-merge your own LICENSED claims |
| 2 | Invited by admin; named in a `domains/<d>/_domain.yml` | Merge LICENSED+PENDING in your domain |
| 3 | ≥6 months as Tier 2 + ≥30 PRs approved without rollback | Full merge for your subspace |

## 7. Attribution

Every claim names:
- The **submitting agent** (Claude model + version + session hash + harness version)
- The **human contributor** (your GitHub login, optional ORCID, optional ROR)
- Every **MCP tool call** your agent made (server + tool name + args hash + response hash)
- Every **dataset** cited (ID + license + snapshot date)
- Any **prior claims** this one depends on / extends / contradicts / supersedes / replicates

This goes in the claim's `provenance` block and is machine-queryable via the viewer.

## 8. PHI and licensing

**Zero PHI** in this repository. Ever. Enforced by:
1. A checkbox on the PR template.
2. An evaluator PHI heuristic (regex scan for DOB/MRN patterns in `claim.text` and `notes`).
3. A corpus-rebuild scan for date / MRN / clinical-narrative patterns.
4. `CODEOWNERS` on `domains/clinical/` requiring Tier-3 review (Phase 2+).

De-identified aggregates only. Claims may reference cohort summary statistics; never individual-level records.

All **claim structure and text** is licensed [CC-BY-4.0](./LICENSE). **Cited data** inherits its upstream license — declare it per-claim in `provenance.datasets_cited[*].license`. If your upstream has commercial restrictions, set `license.restrictions: ["non_commercial_upstream"]`; that's a warning downstream, not a block.

By opening a PR you agree your contribution is CC-BY-4.0-compatible. No CLA, no copyright assignment.

## 9. Disputes and supersession

If your claim contradicts an existing one, declare it in `relations.contradicts: ["<claim-id>"]`. The viewer will render both as a side-by-side dispute card. Resolution is itself a claim (`claim_type: dispute_resolution`) filed as a new PR by a domain reviewer. Losing a dispute is not punished — scientific revision is the point; only fraudulent claims incur tier consequences.

## 10. Adversarial behavior

Gates stack: schema + content hash, evaluator verdict, GitHub identity, per-tier rate limits, PHI heuristic, dense-citation-subgraph detection, no-computation-claim flag, 100%-positive publication-ratio flag, post-merge flagging. See `GOVERNANCE.md` §8.

---

Questions? Open a [discussion](https://github.com/beldez01/polymer-claims/discussions) or ping [@polymergenomics](https://x.com/polymergenomics).
