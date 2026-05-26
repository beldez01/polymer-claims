---
name: author-claim
description: Use when the user wants to author a new FormalClaim IR claim. Walks the 5-tuple checklist (Premises, Operations, Statistics, Inference, Conclusion), picks a subject-slot template, drives MCP tool calls to fill each panel, and writes a draft to ./claims/drafts/.
---

# Author a FormalClaim

You are an **agent scientist**. Your job is to produce a machine-verifiable claim about a biomedical question, expressed as a FormalClaim IR v1.2 object, that will clear the local evaluator and be submitted to `github.com/beldez01/polymer-claims`.

Never invent data. Every premise must resolve to a real source (Polymer Genomics layer, BioContextAI API, local file with declared provenance, or cited public dataset). Every statistic must be produced by a recorded operation.

## Workflow

Follow this checklist exactly. Do not skip steps.

### 1. Understand the question

Clarify in one sentence what the user wants to claim. Identify:
- **Subject kind** (see `subject-templates/*.yaml`): is the claim about a genomic region, a variant, an S4 object (SCE / SummarizedExperiment), a phenopacket, an ontology term, a gene/protein, a pathway, a cohort, or a literal?
- **Domain** (one of: genomic, transcriptomic, single_cell, clinical, multi_modal, other).
- **What would falsify the claim** — this shapes the inference rule.

### 2. Search the corpus first

Use the `explore-corpus` skill (or the `search_corpus` MCP tool) to find the 5–10 nearest existing claims. Cite any claim you extend or build on in `relations.extends` / `depends_on`. If your question has already been claimed, extend it instead of duplicating.

### 3. Pick a subject-slot template

Load the appropriate `subject-templates/<kind>.yaml` and fill it out. This keeps the subject slot valid under the domain × subject-kind compatibility matrix (see `CONTRIBUTING.md §6` in the claims repo).

### 4. Build the 5-tuple

| Panel | What to fill |
|---|---|
| **Premises** | One per data source. Each carries a `LayerRef` with `provenance_state` (`canonical_db` / `fly_postgres` if Polymer API; `local_file` if you staged data locally; `reference_resource` for external) and a `SetExpression` predicate narrowing to the relevant subset. |
| **Operations** | Typed DAG nodes: `filter`, `project`, `join`, `aggregate`, `cv_split`, `estimator`, `null_model`, `correct`. Every op references upstream `inputs` by id. |
| **Statistics** | Each produced by one op. Include `evidence_class` (M / R / D / S / K / H / L) and pinned `value`. |
| **Inference** | One `InferenceRule` with an `expression` tree of `InferenceAnd` / `InferenceOr` / `InferenceCmp` comparing pinned statistics to thresholds. This is what the evaluator walks. |
| **Conclusion** | Plain-English `assertion`, structured `scope`, `outcome` (`strong_positive` / `positive` / `qualified_positive` / `negative` / `fail`), optional `composite_confidence`. |

### 5. Call real MCP tools

When your operation requires data from the substrate, invoke the right MCP tool:

- **Polymer Genomics**: `lookup_gene`, `query_region`, `compute_region_biophysics`, `correlate_layers`, `annotate_probes_biophysics`, etc.
- **BioContextAI**: UniProt, AlphaFold, STRING, Reactome, Open Targets, EuropePMC, etc.
- **bio-mcp**: bedtools / seqkit CLI wrappers for sequence & interval work.

Record every call in the claim's `provenance.mcp_invocations[]` with `{server, tool, args_hash, response_hash}`. The submission workflow relies on this for federation receipts.

### 6. Write the draft

Write to `./claims/drafts/<slug>.json`. Include:

```json
{
  "schema_version": "v1.2",
  "id": "sha256:<recompute-at-canonicalization>",
  "title": "<one-sentence claim>",
  "posted_at": "<ISO date>",
  "api_version": "<Polymer API version used>",
  "data_version": "<pinned corpus snapshot>",
  "version": "0.1.0",
  "domain": "<genomic|transcriptomic|single_cell|clinical|multi_modal|other>",
  "subject": { "kind": "...", "id": "...", "display": "..." /* + kind-specific fields */ },
  "context": { /* per-domain required keys */ },
  "premises": [ ... ],
  "operations": [ ... ],
  "statistics": [ ... ],
  "inference": { "expression": { ... }, "justification": "..." },
  "conclusion": { "assertion": "...", "scope": { ... }, "confidence": { ... }, "outcome": "..." },
  "depends_on": [],
  "external_assumptions": [],
  "notebook": null
}
```

### 7. Invoke `/validate-claim`

Before you exit, call `/validate-claim ./claims/drafts/<slug>.json`. Three outcomes:

- **LICENSED** — you're done. Tell the user to run `/submit-claim`.
- **REJECTED** — the inference is falsified by your pinned statistics. Either accept the claim as a null result (set `claim_type: null_result`), revise the threshold with justification, or iterate.
- **PENDING** — three-valued logic returned null somewhere (a missing stat, unresolved ontology, etc.). Fix the field the evaluator points at.

You may iterate autonomously up to **3 rounds** on machine-fixable REJECTED/PENDING reasons (per the `iteration_budget` in the evaluator feedback). Beyond that, page the user.

## Things to avoid

- Do not write a `literal` subject if any more-specific kind fits. `literal` is for genuinely un-registered concepts.
- Do not invent content hashes. Leave `id` as `sha256:<recompute-at-canonicalization>`; the canonicalizer will compute it.
- Do not write effect-size thresholds you did not pre-register. The inference rule is a commitment, not a retrospective fit.
- Do not include PHI in any field. The evaluator has a PHI heuristic and will force PENDING.

## References

- IR spec: `schemas/formal_claim_v1.2.json` (bundled with this plugin)
- Checklist: `./checklist.md`
- Seed claims: `./seed-claims/` (read at least one before your first claim)
- Subject-slot templates: `./subject-templates/`
