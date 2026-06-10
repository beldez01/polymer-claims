# Claim Evidence Socket (CES) — Interface Contract

**Status:** Design / interface contract (not implementation). v0.1
**Date:** 2026-06-09
**Author:** Z. Belden
**Scope:** the connective tissue between **Polymer EOS** (`polymer_grammar` / `polymer_protocol`,
`~/Desktop/polymer-claims/`) and **Polymer Genomics** (the SE Contract + R-Engine/Boris stack,
`~/Desktop/Polymer/`). Defines *how a claim points at real experimental data and a real
computation, and how the result flows back into licensing* — without moving bulk data across any
API and without a grammar redesign.

---

## 0. One-paragraph idea

An EOS `Claim` already carries an executable `evaluation_plan` = a compute-graph DAG whose
`OperationNode`s have `inputs` (including a `DataHandle`), an `impl` dispatch key, and `params`,
terminating in a `SatisfactionCriterion`. Today those slots are *thin*: `DataHandle.ref` is a bare
string, `impl` is a toy (`builtin::const`), and a "license" therefore means "the model's number
beat the model's threshold." Polymer Genomics independently built the *thick* versions of every one
of those slots: the **SE Contract** (a content-addressed, hash-verified manifest of a
SummarizedExperiment), the **Boris tool registry** (82 real R/Bioconductor methods), and
**SemanticRunID + DecisionEvent** (a content-addressed reproducibility/provenance trace). The Claim
Evidence Socket is the contract that **binds the thin EOS slots to the thick Polymer objects**, so a
claim can be licensed by a real DESeq2/ChAMP run over content-addressed data, drift-checked against
the data's hash, and capped by the data's validation tier.

---

## 1. The invariants the socket must preserve

1. **No bulk bytes through the API.** Polymer law (`BACKEND_STRUCTURE.md`): *"Large data NEVER
   passes through the API… if bytes touch the API, the design is wrong."* The socket carries only
   handles, parameters, hashes, and scalar/small results — never assay matrices.
2. **The EOS air-gap.** A claim licenses only when **≥2 independently-identified adapters** execute
   the plan and **agree** on a **SATISFIED** verdict. The socket must define what "independent"
   means once a real external compute substrate is involved (see §5).
3. **Materialization is recorded.** Every `Satisfaction` records the exact data + apparatus version
   it was checked against, so the drift daemon can later detect staleness (see §3, §7).
4. **External generation can propose but never license.** Unchanged: claims arriving from any
   untrusted source pass through `compile_untrusted`; the socket is an *execution/verification*
   seam, not a generation bypass.

---

## 2. The three bindings (the heart of the contract)

### B1 — `DataHandle` → SE Contract reference  *(the data seam)*

**EOS side today:** `DataHandle.ref: str` (opaque string).
**Polymer side today:** `SEContract` with `uid`, `dimnames_hash` (SHA256 of
`feature_ids|sample_ids`), `dim`, `assays[]`, `col_data[]`, `row_data[]`, and
`extensions.storage_hints.assay_refs` (HDF5/Zarr/S3/recomputable pointers). Resolvable via
`ContractLoader.load_by_ref(uid | accession | key)`.

**Contract:** `DataHandle.ref` resolves to a **content-addressed SE Contract reference** carrying,
at minimum:

| Field | Meaning | Source |
|---|---|---|
| `contract_uid` | the dataset's stable handle | SEContract.uid |
| `dimnames_hash` | **canonical content-address** (SHA256) | SEContract.dimnames_hash |
| `assay` | which assay the claim reads (e.g. `beta`, `counts`) | SEContract.assays[].name |
| `selection` | row/col/subgroup selector (e.g. `group=Treatment`) | params over col_data/row_data |
| `genome_assembly` | build, ideally as a **refget digest** not `"hg38"` | SEContract.metadata + refget |
| `access` | DRS-shaped `access_methods[]` (s3/https/file) | storage_hints |

**Crucial design choice (from prior-art review):** shape this reference like a **GA4GH DRS object**
(`self_uri`, `size`, `checksums[]`, `access_methods[]`) so any GA4GH-aware client can resolve it —
but keep our **`dimnames_hash` as the canonical ID**. DRS deliberately makes its `id` host-assigned
and its checksum mere *fixity metadata*; it has **no content-derived identity**. That is precisely
the gap our SE Contract fills, so we are a *richer, content-addressed DRS*. We do **not** stand up a
full DRS server unless a consortium partner requires it — we adopt the *shape*.

The API returns only this reference (small JSON). The bytes are realized **where the compute runs**
(see B2), never in transit through the claims API.

### B2 — `OperationNode.impl` → Boris tool registry  *(the compute seam)*

**EOS side today:** `impl: str` dispatched by an `Adapter`; only `builtin::*` reference impls exist.
**Polymer side today:** `tool_registry.json` (82 methods: `deseq2_de`, `champ_dmp`, `marlin_classify`,
`vaf`, …) executed on the R-Engine via `PlumberClient`.

**Contract:** an `OperationNode.impl` in the namespace **`boris::<tool_id>`** denotes a registered
Boris tool. A **`BorisExecutionAdapter`** implements the EOS `Adapter` Protocol:

- `identity` = a stable string identifying *this method as run by this engine version* (used by the
  air-gap; see §5).
- `execute(node, upstream, ctx)`:
  1. resolves the node's `DataHandle` to an SE Contract reference (B1);
  2. instructs the R-Engine to **materialize the assay locally/in-worker** from `storage_hints`
     (R side: a `SummarizedExperiment` whose assay is a **`DelayedArray`/`HDF5Array`** — *not*
     `restfulSE`, which was removed at Bioconductor 3.20; Python side: anndata `read_lazy` over
     Zarr v3 if the substrate is AnnData-shaped);
  3. runs `boris::<tool_id>` with `params`;
  4. returns a small `ExecValue` (the scalar/vector the criterion consumes) — **never the matrix**.
- `produces` (the node's `ProducedLeafSpec`) must match the tool's output leaf kind (e.g.
  `deseq2_de` → a `quantity` leaf such as an effect size or an FDR).

This makes the EOS compute-graph and the Polymer tool registry **converge on one dispatch
vocabulary**: a claim's plan is literally "run tool T with params P over dataset D, compare the
result to threshold θ."

### B3 — `Satisfaction.materialization` → SemanticRunID  *(the provenance seam)*

**EOS side today:** `Satisfaction.materialization: MaterializationContext(api_version, data_version)`.
**Polymer side today:** `SemanticRunID = SHA256(tool | param_signature | input_signature)` where
`input_signature = SHA256(sorted input contract hashes)`; plus `DecisionEvent` (chosen value,
rationale, alternatives rejected).

**Contract:** when a `BorisExecutionAdapter` mints a result, the `MaterializationContext` is
extended to carry:

| Field | Meaning |
|---|---|
| `semantic_run_id` | SHA256(tool · params · input contract hashes) — the reproducibility key |
| `contract_uid` + `dimnames_hash` | which dataset, content-addressed (the drift key, §7) |
| `tool_id` + `param_signature` | which computation |
| `engine_version` | `bioc_version` / `r_version` / api version (apparatus identity) |

The `SemanticRunID` **is** the materialization identity: two runs that produce the same
`semantic_run_id` are the same evidence, regardless of machine or time. This is the natural key the
EOS drift daemon and the `LicenseRoute.REPLICATION` test already want.

---

## 3. End-to-end flow (PENDING claim → LICENSED)

```
PENDING claim with evaluation_plan
  → SELECT picks it (value vs cost; EIG)
  → EXECUTE/VERIFY:
      for each of ≥2 independent adapters (see §5):
        resolve DataHandle → SE Contract ref            [B1, API: metadata only]
        materialize assay locally/in-worker             [DelayedArray/HDF5Array | read_lazy]
        run boris::<tool> with params                   [B2, R-Engine; bytes stay put]
        return ExecValue                                 [scalar/vector only]
      agreement gate: ≥2 distinct identities + agree
      criterion comparison → verdict
  → if agreement ∧ SATISFIED:
      mint Satisfaction with materialization =
        { semantic_run_id, contract_uid, dimnames_hash, tool_id, engine_version }   [B3]
      ValidationTier ceiling caps strength               [§6]
      Licensing(route, rival_set_closure) ⇒ status = LICENSED
  → INTEGRATE (defeat edges, restore consistency)
```

Result: a claim whose license is earned from real, content-addressed experimental data via a real
Bioconductor computation, fully reproducible and drift-trackable — and **no assay byte ever crossed
the claims API**.

---

## 4. The air-gap independence problem  *(a real decision, not a detail)*

The EOS air-gap requires **two independent adapters that agree**. With `builtin::const` or two
independently-coded arithmetic adapters, independence is genuine. With a single external compute
engine, two adapters hitting the **same** R-Engine endpoint are **not** independent — they would
agree trivially, silently downgrading "verified by replication" to "the API returned a consistent
value." The socket must pick how independence is achieved per claim. Map each to a `LicenseRoute`:

- **Methodological independence → `SEVERE_TEST` (or `REPLICATION`):** two *different tools* compute
  the same quantity (e.g. `deseq2_de` vs `edger_de` / `limma_voom` for the same contrast; a region
  mean vs a probe-level aggregate). Agreement across methods is a real check. **Default for CES.**
- **Materialization independence → `REPLICATION`:** the same tool over **two independent
  materializations** — different cohort splits, batches, or dataset versions (distinct
  `dimnames_hash`). This is the strongest and the natural `REPLICATION` route.
- **Implementation independence → `SEVERE_TEST`:** a recomputation from rawer data by an
  independently-coded path.

**Rule:** a `BorisExecutionAdapter`'s `identity` must encode *(tool, engine)*, so two nodes using
the same tool+engine cannot count as two identities. The plan author (LLM or operator) must supply a
genuinely independent second leg; the verifier enforces distinct identities. **No air-gap theater.**

---

## 5. Validation-tier assignment from substrate

The substrate's nature sets the `OracleDossier.validation_tier`, which caps the claim's empirical
strength axes (`UNVALIDATED 0.0 → INDIRECT 0.4 → BENCHMARKED 0.6 → ANCHORED 0.85 → GOLD 1.0`):

| Substrate | Example | Tier (ceiling) |
|---|---|---|
| Direct wet-lab / clinical anchor | sorted-cell EM-seq, our 48-sample cohort | ANCHORED (0.85) |
| Recomputable experimental data | a public GEO/TCGA methylation matrix as SE Contract | BENCHMARKED (0.6) |
| Computed/predicted reference | predicted biophysics from Polymer Genomics | BENCHMARKED→INDIRECT |
| Literature-reported value | extracted from a paper (future literature API) | INDIRECT (0.4) |
| Unvalidated / out-of-domain apparatus | — | UNVALIDATED (0.0) |

A claim grounded in weak substrate **renders visibly weak**; it cannot borrow false confidence from
the mere fact that it licensed. This is the patch for "a tower of claims on an unvalidated
foundation."

---

## 6. Drift semantics

The **`dimnames_hash` (and dataset version) is the drift key.** When a referenced SE Contract's
content-hash changes — re-annotation, corrected coordinates, an updated matrix — the EOS
`drift_pass` daemon compares each LICENSED claim's recorded `materialization.dimnames_hash` against
the current contract and **re-PENDINGs** claims whose substrate drifted (`reopen_drifted`). Growing
or correcting a dataset thus cannot silently invalidate downstream claims; it surfaces them for
re-licensing. (Admitting a *new* reference dataset routes through the `representation_revision`
meta-tier — substrate growth is itself a licensable assertion.)

---

## 7. Public / private promotion boundary  *(governance — needs a ruling)*

- **Local node (paid platform):** claims may be licensed against **private** SE Contracts
  (the user's own cohorts). These licenses are valid **in the local universe only**.
- **Public universe:** a claim may hold a **public** license only if its SE Contract is
  **publicly resolvable** (a public accession / DOI'd dataset with a fixed `dimnames_hash`).
- **Promotion rule (proposed):** a privately-licensed claim crossing into the public universe
  arrives as a **CONJECTURE**, not a license — i.e. *private/undisclosed evidence can PROPOSE but
  never publicly-LICENSE* (the same primitive as `compile_untrusted`, applied to evidence). It
  earns a public license only when re-licensed against publicly-reproducible data.

This is the one CES decision **not** patchable by existing code; it is a policy choice. **Open for
the user to ratify.**

---

## 8. Prior-art alignment — what we stand on

From the 2026 landscape review. Principle: **adopt the shapes and IDs that already won; do not
rebuild data hosting.**

**ADOPT / INTEROP:**
- **GA4GH DRS *shape*** for the SE Contract handle (`self_uri`, `size`, `checksums[]`,
  `access_methods[]`) — resolvable by GA4GH clients; keep our `dimnames_hash` as canonical ID
  (DRS's gap). DRS latest 1.5.0 (2024), adoption concentrated in US cloud-genomics consortia — adopt
  the shape, not necessarily a served endpoint.
- **GA4GH VRS computed IDs** (`ga4gh:VA.…`, truncated SHA-512) for the **variant subject slot** —
  replaces any home-grown variant ID; ties into the existing `Subject.VariantVRS` type. **refget**
  digests to pin the genome build instead of the string `"hg38"`.
- **W3C PROV-O** as the provenance vocabulary (Activity = a run_cycle / evaluation; Entity =
  claim / dataset; Agent = operator / adapter), serialized as an **RO-Crate** (Provenance Run Crate
  profile). Our `SemanticRunID`/`DecisionEvent` map onto PROV directly. BagIt/bdbag only if a
  portable, fixity-checked evidence bundle is needed.
- **Storage realizers:** R side = `DelayedArray` + `HDF5Array`/`TileDBArray`; Python side = anndata
  `read_lazy()` over **Zarr v3**. For single-cell-shaped or cross-language-sliced data,
  **TileDB-SOMA** (production-ready, powers CELLxGENE Census) — *verify its SingleCellExperiment
  bridge maturity before betting a Bioc workflow on it.*

**OUTWARD-FACING NICETY:** emit a **Croissant 1.1** sidecar + a **DataCite DOI** for any dataset we
publish, so ML/agent tooling can discover it (fits the BYO-agent north star).

**SKIP for the internal engine:** htsget (file streaming, not handles), Beacon v2 (external
discovery), Phenopackets (only if we attach patient phenotype), Frictionless (too tabular),
raw CWL/WDL, ExperimentHub-style full-download (it moves the bytes — opposite of our constraint).

**DEAD — do not cite/build on:** `restfulSE` (removed at Bioconductor 3.20). Its successor in spirit
is `DelayedArray` + `HDF5Array`/`TileDBArray`.

**The JSON-vs-S4 consensus (validates our SE Contract):** the field has stopped trying to serialize
a live S4 object to JSON. The standard pattern *is* what we built — **separate a small, JSON,
content-hashed handle from the big chunked assay bytes, and rematerialize the object lazily on each
side from its native backend.** Our upgrade is (a) align the handle with DRS, and (b) let both an R
realizer and a Python `read_lazy` realizer consume the same handle.

---

## 9. What exists vs. what's to build

| Piece | EOS (`polymer-claims`) | Polymer Genomics (`Polymer/`) | To build |
|---|---|---|---|
| Compute-graph + DataHandle slot | ✅ exists (thin) | — | enrich handle (B1) |
| Content-addressed dataset object | — | ✅ SE Contract + dimnames_hash | DRS-shape it |
| Compute method registry | toy `builtin::*` | ✅ 82-tool Boris registry + PlumberClient | `BorisExecutionAdapter` (B2) |
| Reproducibility/provenance key | thin (`rationale`) | ✅ SemanticRunID + DecisionEvent | thread into MaterializationContext (B3) |
| Drift detection | ✅ `drift_pass` daemon | hashes available | wire hash → drift key (§6) |
| Tier capping | ✅ ValidationTier / OracleDossier | data-type info | substrate→tier map (§5) |
| Air-gap | ✅ `verify()` (≥2 identities) | multiple methods available | independence policy (§4) |
| Public/private promotion | primitive exists (`compile_untrusted`) | local vs object-store | **policy ruling (§7)** |

**The single highest-leverage first step:** implement B1 + a minimal B2 for *one* tool
(e.g. `boris::champ_dmp` or a region mean-difference) over *one* public methylation SE Contract, and
let a single hematopoiesis claim license through it. That one path lights up the handle, the adapter,
the materialization record, the drift key, and the tier cap at once — because every other piece
already exists on one side or the other.

---

## 10. Open decisions for the user

1. **Public/private promotion policy (§7)** — ratify "private evidence proposes, public data
   licenses," or choose an alternative (verified-but-undisclosed tier; ZK-style fixity proof).
2. **Default air-gap independence (§4)** — confirm *methodological independence* (two tools) as the
   CES default route, vs requiring *materialization independence* (two datasets) for `REPLICATION`.
3. **DRS endpoint vs DRS shape (§8)** — adopt DRS *shape* only (recommended), or stand up a served
   DRS endpoint (only if a partner requires it).
4. **TileDB-SOMA bet (§8)** — whether to commit to SOMA for cross-language slicing now (pending SCE
   interop verification) or stay on HDF5Array/Zarr per substrate.

---

## Appendix — illustrative handle & materialization shapes (contracts, not code)

```jsonc
// DataHandle.ref resolves to (DRS-shaped, content-addressed):
{
  "self_uri": "drs://polymer/se-7f3a…",
  "contract_uid": "se-7f3a9c…",
  "dimnames_hash": "sha256:9b1c…",        // canonical content-address (DRS's gap)
  "assay": "beta",
  "selection": { "group_col": "condition", "group_a": "TET2mut", "group_b": "WT" },
  "genome_assembly": "refget:SQ.Ya6Rs…",   // not the string "hg38"
  "size": 412000000,
  "checksums": [{ "type": "sha256", "checksum": "…" }],
  "access_methods": [
    { "type": "s3",   "access_url": "s3://…/beta.h5" },
    { "type": "https","access_url": "https://…/beta.h5" }
  ]
}
```

```jsonc
// Satisfaction.materialization (B3) recorded at license time:
{
  "semantic_run_id": "sha256:c84d…",       // SHA256(tool · params · input hashes)
  "contract_uid": "se-7f3a9c…",
  "dimnames_hash": "sha256:9b1c…",          // drift key
  "tool_id": "boris::champ_dmp",
  "param_signature": "sha256:1f02…",
  "engine_version": "bioc-3.22/r-4.5.2"
}
```
```
```
