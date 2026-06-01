# FormalClaim authoring checklist

Use this as a literal checklist. If any line is incomplete, the claim is not ready.

## Subject & domain
- [ ] Subject kind chosen and fits the domain's legal set.
- [ ] Subject `id` canonical (CURIE, VRS ID, content hash — not prose).
- [ ] Domain's `context` envelope populated (e.g. `assembly` for genomic, `assay` + `organism` for transcriptomic).

## Premises
- [ ] Each premise cites a real source with `LayerRef {layer, version, provenance_state}`.
- [ ] `predicate` narrows to the subset this claim reasons over.
- [ ] `content_hash` recorded (or placeholder flagged for canonicalization).

## Operations
- [ ] Every operation has a unique `id`.
- [ ] Every `inputs[i]` references an existing premise or op id.
- [ ] `EstimatorOp.estimator.impl` uses a recognized namespace prefix (`scipy.stats.*`, `R::*`, `python::sklearn.*`, `python::polymer_genomics.stats.*`).
- [ ] `FeatureSet` used for dynamic column subsets (not string lists).

## Statistics
- [ ] Every statistic has a `produced_by` matching an op id.
- [ ] `evidence_class` set (M=measured, R=recorded, D=derived, S=statistical, K=curated, H=hypothetical, L=literal).
- [ ] `value` is pinned (no placeholder).

## Inference
- [ ] `expression` tree uses only `InferenceAnd` / `InferenceOr` / `InferenceNot` / `InferenceCmp`.
- [ ] Every `InferenceCmp.lhs.stat_id` resolves to a real `Statistic`.
- [ ] Thresholds are pre-registered in `justification` — not fit to the pinned values post-hoc.

## Conclusion
- [ ] `assertion` is one sentence, ≤280 chars, plain English.
- [ ] `scope.layers` lists every layer the claim applies to.
- [ ] `outcome` matches the inference tree's licensed verdict (strong_positive / positive / qualified_positive / negative / fail).
- [ ] If `composite_confidence` present, `procedure` and `impl` are specified.

## Provenance
- [ ] `provenance.submitting_agent` populated by the harness.
- [ ] `provenance.mcp_invocations[]` contains one entry per MCP tool call.
- [ ] `provenance.datasets_cited[]` has license for every external dataset.
- [ ] `provenance.prior_claims_referenced[]` names every claim you depend on / extend / contradict / supersede / replicate.

## Final
- [ ] `/validate-claim` returned **LICENSED** (or you accept a null-result claim).
- [ ] No PHI anywhere in `claim.text`, `notes`, or `literal` fields.
- [ ] You have declared any upstream license restrictions in `license.restrictions`.
