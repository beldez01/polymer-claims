# The measurement-space registry — one catalog, two consumers

**Date:** 2026-07-14
**Status:** Design (authored by the backlog loop; both Spec 1 §7 and Spec 2 §7/§11 *deferred*
the registry schema, so this is that deferred spec). Minimal, additive, umbrella-side v1.

---

## 0. One-paragraph summary

The accumulating-universe store (Spec 1) and the re-parameterization evaluator (Spec 2) each need
the same missing thing: **a keyed catalog of the measurement spaces the system actually has data
for.** One registry, two consumers — the store reads it as "which measurement spaces does this
subject have claims/data over" (the coverage census), the evaluator reads it as "which apt space is
available to re-parameterize into" (grounding an LLM's mechanistic proposal against real data). In
this codebase a **measurement space is a `(contract_uid, row_prefix)` pair** — e.g.
`gdsc_pharmaco@1`/`meth::` (gene-body methylation) vs `gdsc_pharmaco_promoter@1`/`meth::` (promoter
methylation) are two distinct spaces over the same cell lines, and `auc::`/`expr::`/`cg…` are other
prefixes. No such registry exists today: contracts are discovered by filename, modality strings are
hard-coded and un-unified across collectors, and — the load-bearing gap — **scale-type and
invariance-group metadata live only on `Pattern` (free-form strings), never bound to a measurement
space.** So the registry is also the home that finally binds each space's Stevens scale-type and
admissible-transformation (invariance) group, satisfying the measurement-foundation discipline the
build otherwise only declares-but-never-enforces (backlog §9). v1 is a plain, curated, umbrella-side
catalog with a small query API; grammar/protocol untouched, `Corpus` stays 4.

---

## 1. Foundations alignment

| Foundation | Requirement | How this honors it |
|---|---|---|
| Measurement seam (`measurement-foundation.md` §3.1) | A claim earns standing only if its criterion is invariant under the scale's admissible transformations; every measurement field declares its scale-type + invariance group. | The registry is the first structure that binds `scale_type` (Stevens) + `invariance_group` to a concrete measurement space. A test asserts **every** entry declares both — the definition-of-done the discipline names. This does not yet *enforce* the invariance check at license time (that is the separate §9 HARDEN item); it supplies the metadata that check will read. |
| Purity / Corpus (`epistemology.md` §7; `GLOSSARY.md`) | `Corpus` = exactly 4 collections; grammar/protocol pure + numpy-free. | Entirely umbrella-side (`src/polymer_claims/measurement_space.py`). No grammar/protocol change, no new `Corpus` collection, no new IR field. |
| de Bruijn kernel (`epistemology.md` §8) | Proposers are untrusted; the harness grounds them. | The registry is exactly the grounding surface for the evaluator's LLM proposer (Spec 2, Decision 1): it can only return a space that is *registered and whose contract resolves*, so a hallucinated space yields `None`, never a fabricated re-test. |
| Store / modality's two moments (Spec 1 §4) | Realized modality is a stable, auditable fact you census over. | The registry catalogs the realized modality per space with a **controlled `Modality` vocabulary**, unifying today's ad-hoc strings (`methylation_genebody` / `methylation_promoter` / plain `methylation` / `literature`). The census (Spec 1 §5) is a query over this catalog. |
| Residualism / additive (`residualism.md`; `feedback_ir_monotonic_expansion`) | Additive, never narrowing; catalogs grow. | The catalog is append-only in practice (add spaces as contracts land). Entries are content-identified by `space_id` so they can *later* be promoted to attackable meta-claims (deferred, §5) without a schema break. |

---

## 2. What a measurement space is (grounded in the real code)

Ground truth (from a full code map, 2026-07-14):
- A **contract** (`SEContractRef`, `contracts/__init__.py`) is identified by `contract_uid` = `<stem>@<version>` (the `se:` in a ref is a stripped scheme prefix). It carries `assay` (`"value"`/`"tpm"`/`"beta"`), `genome_assembly`, `dimnames_hash`; **no modality, scale, or invariance field.**
- A contract's rows are namespaced by a **`row_prefix`** in `feature_id` (`meth::<GENE>`, `auc::<DRUG>`, `expr::<GENE>`, `cg…` probes). A plan reads a specific prefix via its `params` (e.g. `pharmaco_adapters.py` builds `meth::{marker}` / `auc::{drug}`).
- "Re-parameterize gene-body → promoter" (Spec 2's motivating case) is realized as **re-issuing the same claim with `data_ref` pointed at a different `contract_uid`** (`gdsc_pharmaco_promoter@1`), same `meth::` prefix. So modality is realized as **contract-id identity**, not a column or a runtime-read flag.

Therefore a **measurement space** is the unit a plan can point at: **`(contract_uid, row_prefix)`**.
Its `space_id` is `"<contract_uid>::<row_prefix>"` (e.g. `"gdsc_pharmaco@1::meth"`).

### 2.1 The `MeasurementSpace` record (frozen)

```
space_id:          str                 # "<contract_uid>::<row_prefix>", stable identity
contract_uid:      str                 # "gdsc_pharmaco@1"  (NO se: prefix — matches SEContractRef)
row_prefix:        str                 # "meth" | "auc" | "expr" | "cg"
modality:          Modality            # controlled enum (unifies today's ad-hoc strings)
scale_type:        ScaleType           # Stevens: RATIO | INTERVAL | ORDINAL | NOMINAL
invariance_group:  str                 # admissible-transformation group (aligned w/ Pattern strings)
units:             str | None = None   # UCUM where meaningful; None for dimensionless/relative
genome_assembly:   str | None = None   # "hg38"
description:       str                 # one-line human note
```

`Modality` (controlled v1): `METHYLATION_GENEBODY`, `METHYLATION_PROMOTER`, `METHYLATION_CPG`,
`EXPRESSION_TPM`, `DRUG_RESPONSE_AUC`. (Non-contract-backed arms like `literature` are out of scope —
the registry is over contract-backed spaces only.)

`ScaleType` (Stevens): `RATIO`, `INTERVAL`, `ORDINAL`, `NOMINAL`.

Invariance groups (reuse existing `Pattern` conventions where they exist):
`bounded_beta_normalization` (methylation β ∈ [0,1]), `monotone_expression_rescaling` (TPM, matches
`expression_floor_patterns.py`), `monotone_dose_response_rescaling` (AUC).

### 2.2 The v1 catalog (real contracts on disk)

| space_id | modality | scale | invariance | assay |
|---|---|---|---|---|
| `gdsc_pharmaco@1::meth` | METHYLATION_GENEBODY | RATIO | bounded_beta_normalization | value |
| `gdsc_pharmaco@1::auc` | DRUG_RESPONSE_AUC | RATIO | monotone_dose_response_rescaling | value |
| `gdsc_pharmaco_promoter@1::meth` | METHYLATION_PROMOTER | RATIO | bounded_beta_normalization | value |
| `gdsc_pharmaco_promoter@1::auc` | DRUG_RESPONSE_AUC | RATIO | monotone_dose_response_rescaling | value |
| `tcga_laml_fusion_expr@1::expr` | EXPRESSION_TPM | RATIO | monotone_expression_rescaling | tpm |
| `target_aml_fusion_expr@1::expr` | EXPRESSION_TPM | RATIO | monotone_expression_rescaling | tpm |
| `tcga_laml_cbf_expr@1::expr` | EXPRESSION_TPM | RATIO | monotone_expression_rescaling | tpm |
| `target_aml_cbf_expr@1::expr` | EXPRESSION_TPM | RATIO | monotone_expression_rescaling | tpm |
| `tcga_laml_idh@2::cg` | METHYLATION_CPG | RATIO | bounded_beta_normalization | beta |

(Extensible — add spaces as contracts land. Gitignored real-data contracts may be *registered* but
`available()` False until present.)

---

## 3. Query API (the two consumers)

All pure, umbrella-side:
- `all_spaces() -> tuple[MeasurementSpace, ...]` — the whole catalog, deterministically sorted by `space_id`.
- `get_space(space_id) -> MeasurementSpace | None`.
- `spaces_for_modality(modality) -> tuple[...]`.
- `spaces_for_contract(contract_uid) -> tuple[...]`.
- `available_spaces(root=None) -> tuple[...]` — filters to spaces whose contract actually resolves via
  `load_contract` (**grounding: what data exists** — the de Bruijn separation). Never raises on a
  missing contract; just omits it.
- `resolve_space(modality, *, exclude_space_id=None, root=None) -> MeasurementSpace | None` — the
  **evaluator's grounding step**: given a target `Modality` (from the LLM's mechanistic reasoning),
  return one available space of that modality (excluding the original), or `None`. Never
  fabricates. Several may match (e.g. `EXPRESSION_TPM` has four spaces) — returns the first by
  sorted `space_id` (deterministic); enumerate all matches with `spaces_for_modality` + availability.
- `coverage() -> Mapping` — catalog grouped by `(modality, scale_type)` for the store's census
  (mirrors `pattern.registry.coverage()`); a plain report, no meta-claims.

---

## 4. Testing strategy (behavior, not implementation)

- **Catalog completeness.** `all_spaces()` contains the expected `space_id`s for the real contracts; every id is unique; sort is deterministic.
- **Discipline enforced.** *Every* entry declares a non-empty `scale_type` (a real `ScaleType`) and `invariance_group` — the measurement-foundation definition-of-done. (A registry entry missing either fails the suite.)
- **Grounding, no fabrication.** `resolve_space(METHYLATION_PROMOTER)` returns the promoter space; `resolve_space(<a modality with no available contract>)` returns `None`. `available_spaces()` omits a space whose contract file is absent (drive via a `using_contract_root` pointed at an empty dir).
- **Exclusion.** `resolve_space(METHYLATION_PROMOTER, exclude_space_id="gdsc_pharmaco_promoter@1::meth")` does not return the excluded space (returns `None` if it was the only promoter space) — the evaluator must not re-propose the space it is re-parameterizing away from *into itself*.
- **Modality unification.** `spaces_for_modality(METHYLATION_GENEBODY)` and `METHYLATION_PROMOTER` are disjoint and both non-empty — the gene-body/promoter split the reparam case needs.
- **Contract grounding is real.** A registered `space_id` whose `contract_uid` resolves is `available`; the resolve path uses the actual `load_contract`, not a stub.
- No grammar/protocol tests change; no byte-identity concern (no serialized-IR change).

---

## 5. Scope discipline / deferred

- **Entries as attackable meta-claims** — Spec 1 §5 and Spec 2 §11 both want registry entries to
  eventually be *licensable* meta-claims (a space's scale-type/invariance is itself a defeasible
  assertion). v1 is a **plain catalog**; `space_id` is content-stable so promotion is additive later.
- **Maps between spaces** (re-parameterization edges, methylation→expression cross-assay relations)
  are **out of scope** — the reinterpret edge (Spec 2 §4) and cross-assay licensable claims
  (backlog §9) own those. The registry catalogs spaces, not maps.
- **Reconciling `merge_universes` hard-coded modality strings** to this controlled vocabulary is a
  follow-up (don't rewire the collectors in this slice; note the drift).
- **Enforcing the invariance check at license time** is the separate §9 HARDEN item; this registry
  supplies the metadata it will consume.

---

## 6. Build order

1. `ScaleType` + `Modality` enums + `MeasurementSpace` frozen record (`src/polymer_claims/measurement_space.py`).
2. The v1 catalog (§2.2) + query API (§3).
3. Tests (§4). Fast gate. Merge local.

## See also
- `specs/2026-07-10-accumulating-universe-store-design.md` §4–§7 (consumer 1) ·
  `specs/2026-07-10-reparameterization-evaluator-design.md` §7 (consumer 2) ·
  `notes/2026-07-14-foundations-digest-for-loop.md` (measurement discipline) ·
  backlog §9 "consume `invariance_group`".
