# claim-harness

> ⚠️ **v1.2 — FROZEN / LEGACY.** This harness authors and validates **v1.2 FormalClaim** drafts.
> It does **NOT** exercise the active v1.3 grammar/protocol runtime. The active path is the v1.3
> local node — `polymer-claims serve` + the `viewer/` app (see the repo-root `README.md` and
> `ARCHITECTURE_CURRENT.md`). This plugin is kept installable as a legacy fallback; a v1.3
> authoring harness does not exist yet.

The Polymer Claims harness for Claude Code — turns your session into an **agent scientist** that can author machine-verifiable biomedical claims against the Polymer Genomics substrate and submit them to the public corpus at [github.com/beldez01/polymer-claims](https://github.com/beldez01/polymer-claims).

## Install

```bash
claude /plugin marketplace add beldez01/polymer-claims
claude /plugin install claim-harness@polymer-claims
```

## What you get

- **MCP servers** — Polymer Genomics (70 tools, 48 layers), BioContextAI Knowledgebase (14 APIs), bio-mcp CLI wrappers (bedtools, seqkit), and the bundled `claim-ir` MCP (`validate_claim`, `evaluate_claim`, `search_corpus`, `query_neighbors`, `fetch_claim`, `check_contradictions`).
- **Skills** — `/author-claim`, `/validate-claim`, `/submit-claim`, `/explore-corpus`.
- **Subagent** — `claim-author` for deeper multi-step authoring.
- **Hooks** — `PreToolUse` evaluator gate (no REJECTED/PENDING submissions), `SessionStart` corpus refresh.
- **Schema** — FormalClaim IR v1.2 JSON Schema, offline-resolvable.
- **Seed claims** — three exemplar claims (Exp 17 recombination, Exp 03 TE silencing, Exp 16 HLA-A ΔG37) for corpus-as-documentation onboarding.
- **Subject templates** — YAML stubs for genomic region, variant, gene, ontology term, cohort.

## First claim

```
> /author-claim "Do LINE-1 TEs in H3K9me3-enriched regions show lower ΔG37 variance than expected under GC null?"
```

Target time to first LICENSED draft on a familiar question: **~7 minutes**.

## Repository

- Marketplace: [beldez01/polymer-claims](https://github.com/beldez01/polymer-claims)
- Claims corpus: [beldez01/polymer-claims](https://github.com/beldez01/polymer-claims)
- Evaluator + IR library: `pip install polymer-formalclaim` (PyPI)
- Portal / viewer: [polymerbio.org](https://polymerbio.org)

## License

MIT. See `LICENSE`.

Your generated FormalClaim objects are CC-BY-4.0 once merged to the corpus (same license as `beldez01/polymer-claims`). Upstream data inherits its own license, declared per claim.
