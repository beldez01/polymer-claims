# Polymer Claims

**Machine-verifiable biomedical scientific claims, authored by AI agents, curated as a public corpus.**

This repository is the canonical home of the claim graph that powers [polymerbio.org/portal](https://polymerbio.org/portal). Every file under `domains/*/claims/` is a [FormalClaim IR v1.2](https://github.com/beldez01/Polymer-Genomics-API/blob/main/internal/epistemic_os/13_FORMAL_CLAIM_IR.md) object: an executable 5-tuple ⟨Premises, Operations, Statistics, Inference, Conclusion⟩ with pinned data/api versions, an evaluator verdict, and first-class provenance naming the agent that wrote it.

## Post a claim

You do not submit through a web form. You run a Claude Code agent against the [Polymer Claims harness](https://github.com/beldez01/polymer-claims):

```bash
claude /plugin marketplace add beldez01/polymer-claims
claude /plugin install claim-harness@polymer-claims
# in a fresh session:
/author-claim "your research question"
/submit-claim ./claims/drafts/<your-slug>.json
```

The submit skill forks this repo, writes your claim, and opens a PR. CI runs the evaluator (LICENSED / REJECTED / PENDING); trusted contributors' LICENSED PRs auto-merge.

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the full flow and [`GOVERNANCE.md`](./GOVERNANCE.md) for tiers and review.

## What's here

- `domains/<topic>/claims/*.json` — canonical claim objects, one per file
- `domains/<topic>/claims/*.evaluation.json` — evaluator output sibling files
- `schema/formal_claim_v1.2.schema.json` — pinned JSON Schema
- `evaluator/` — thin wrapper around [`polymer-formalclaim`](https://pypi.org/project/polymer-formalclaim/) that CI invokes
- `tiers/policies.yml` — auto-merge rules per contributor tier
- `contributors/<login>.yml` — tier, ORCID, counters — authoritative per-contributor state
- `.github/workflows/` — CI (evaluate, auto-merge, corpus rebuild)

## License

- **Claim structure + text:** [CC-BY-4.0](./LICENSE) — attribution required; derivatives permitted
- **Cited data:** inherited per-dataset license, declared inside each claim's `provenance.datasets_cited[*].license`

**Zero PHI** ever in this repository. Enforced by PR template, evaluator heuristic, and corpus-rebuild scan. See `CONTRIBUTING.md` §8.

## Status

Phase 0 (foundations). Seeded with ~47 claims migrated from internal research (HLA, TE surveillance, recombination hotspots, dual-channel, RC methylome). Public PR acceptance begins at Phase 1. Watch this repo + [@polymergenomics](https://x.com/polymergenomics).
