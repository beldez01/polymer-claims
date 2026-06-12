# CES-1 — the data seam (`DataHandle` → DRS-shaped SE-Contract reference)

**Status:** Design / phase spec. v0.1
**Date:** 2026-06-11
**Author:** Z. Belden
**Depends on:** CES-0 (`2026-06-10-ces-0-analysis-profile-design.md`), the CES interface contract
(`2026-06-09-claim-evidence-socket.md` §B1), the architecture audit
(`2026-06-10-ces-architecture-audit.md` §1–2). Slice 1b (first half) of the credibility-arc
roadmap (`docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md`).
**Decided forks (this session):** CES-1 is the **data seam only** — resolution + content-address +
DRS shape — with **no computation and no claim licensing** (that is CES-2); the fixture is
**synthetic but EPICv2-shaped** (real `cg########` probe-ID format + hg38 coordinates, synthetic
beta values), built entirely in-repo, with the real-vs-public-data decision **parked until CES-2**;
fixture on disk is a **JSON manifest + a sidecar betas matrix file** (mirrors the real SE-Contract
shape, where assays point to external storage).

---

## 0. Goal

Make `DataHandle.ref` resolve to a **content-addressed, DRS-shaped SE-Contract reference**, so that
when CES-2 runs a real computation it reads bytes through a stable, hash-verified handle — and the
license records *which exact dataset* (by content) it was earned over. CES-1 ships only the seam:
the reference type, a bundled methylation SE-Contract fixture, the loader, and the canonical
`dimnames_hash`. It does **not** compute anything or mint a claim.

This is B1 from the interface contract: "the data seam." It sits between CES-0 (which gave the
*analysis* a content address, `profile_hash`) and CES-2 (which licenses a claim on a real computed
scalar). CES-0 already added the `dimnames_hash` field to `MaterializationContext`; CES-1 produces
the value that field will eventually carry.

---

## 1. The load-bearing principle: the handle stays thin (CES-0's law holds)

Per CES-0 §1 and the interface contract's "thin handle" law, the grammar must not absorb the SE
Contract. Therefore:

- **`DataHandle.ref` stays a bare `str`** (`grammar/src/polymer_grammar/operations.py:36`) — a
  stable contract key, e.g. `"se:tet2_epicv2_demo@1"`. **Zero grammar change.**
- All richness — the DRS-shaped reference, the fixture, the loader — lives in the **umbrella
  package** (`src/polymer_claims/contracts/`), exactly mirroring `AnalysisProfile`/`load_profile`
  (`src/polymer_claims/profiles.py`) and `load_dataset` (`src/polymer_claims/datasets/`).
- **`protocol/` is untouched.** The one-way grammar isolation and the Corpus-stays-4 invariant are
  unaffected (no new persisted state; a resolved reference is ephemeral, like a loaded dataset).

---

## 2. The reference type — `SEContractRef` (frozen, umbrella-side)

A frozen model: what `DataHandle.ref` resolves to. It carries the B1-contract fields (interface
contract §B1 table) **plus** the GA4GH-DRS *shape* — we adopt the shape so a DRS-aware client could
resolve it, but we keep our content-derived `dimnames_hash` as the canonical ID (DRS's own `id` is
host-assigned with no content identity — the gap our SE Contract fills). We do **not** stand up a
served DRS endpoint (interface contract §8: shape-only unless a partner requires a server).

```python
class AccessMethod(_Model):
    type: Literal["file", "https", "s3"]
    access_url: str

class Checksum(_Model):
    type: Literal["sha-256"] = "sha-256"
    checksum: str            # hex digest

class SEContractRef(_Model):
    # --- SE-Contract / B1 fields ---
    contract_uid: str                      # stable handle (mirrors SEContract.uid)
    dimnames_hash: str                     # CANONICAL content-address: sha256(feature_ids|sample_ids)
    assay: str                             # which matrix the claim reads, e.g. "beta"
    selection: tuple[tuple[str, str], ...] = ()   # row/col selector, e.g. (("group_col","Sample_Group"),)
    genome_assembly: str                   # "hg38" for the local fixture
    refget_digest: str | None = None       # noted slot; a real refget digest needs the reference genome (out of scope)
    # --- GA4GH DRS shape (fixity) ---
    self_uri: str                          # e.g. "drs://local/tet2_epicv2_demo@1"
    size: int                              # total fixture bytes
    checksums: tuple[Checksum, ...]        # sha-256 over the fixture bytes
    access_methods: tuple[AccessMethod, ...]   # here: one {"type":"file","access_url": <bundled path>}
```

Notes:
- `selection` uses the existing `tuple[tuple[str,str],...]` idiom (same as `OperationNode.params`)
  to stay frozen/hashable and JSON-stable.
- `dimnames_hash` is the **drift key** CES-3 will compare in `drift_pass`; CES-1 only computes and
  exposes it.

---

## 3. The fixture — EPICv2-shaped, synthetic values

Bundled under `src/polymer_claims/contracts/`, structural fidelity with placeholder betas. **Two
files** (the decided sidecar layout):

**`tet2_epicv2_demo.json`** — the SE-Contract manifest:

```jsonc
{
  "uid": "tet2_epicv2_demo@1",
  "dim": [50, 8],                       // [n_features, n_samples] — must match the matrix
  "assays": [{ "name": "beta", "ref": "tet2_epicv2_demo.betas.tsv" }],
  "col_data": [                          // one entry per sample, in matrix column order
    { "sample_id": "S01", "Sample_Group": "TET2_mut", "Age": 54, "Sex": "M" },
    { "sample_id": "S02", "Sample_Group": "WT",       "Age": 49, "Sex": "F" }
    // … 8 samples, balanced TET2_mut / WT
  ],
  "row_data": [                          // one entry per probe, in matrix row order
    { "feature_id": "cg00000001", "chr": "chr4", "pos": 105000000 }
    // … 50 EPICv2 cg-format probes on chr4 near the TET2 locus, hg38 coordinates
  ],
  "metadata": { "genome_assembly": "hg38", "array": "EPICv2" }
}
```

**`tet2_epicv2_demo.betas.tsv`** — the beta matrix: header row of `sample_id`s, then one row per
probe (`feature_id` + 8 beta values in [0,1]). 50 probes × 8 samples. Values are synthetic; for
CES-2's benefit a small subset of probes carries a planted TET2_mut-vs-WT shift (documented in the
fixture, exercised only in CES-2 — CES-1 asserts nothing about values).

**Why synthetic is sufficient for CES-1:** the data seam resolves and content-addresses the dataset;
it never reads a beta value. Real-vs-public betas is a CES-2 decision (it is where values license).

---

## 4. The loader + `dimnames_hash`

`src/polymer_claims/contracts/__init__.py`, mirroring `datasets/__init__.py`:

```python
@lru_cache(maxsize=None)
def load_contract(ref: str) -> SEContractRef:
    """Resolve a DataHandle.ref to a DRS-shaped SE-Contract reference.
    Unknown ref -> FileNotFoundError (the caller degrades it to a node error; never crashes)."""
```

Behavior:
- Map `ref` (`"se:tet2_epicv2_demo@1"` or the bare `"tet2_epicv2_demo@1"`) to the bundled manifest;
  unknown ref → `FileNotFoundError` (same contract as `load_dataset`).
- Read the manifest; extract `feature_ids` (from `row_data`, in order) and `sample_ids` (from
  `col_data`, in order).
- **`dimnames_hash = "sha256:" + sha256(canonical_json({"feature_ids": [...], "sample_ids": [...]}))`**,
  where `canonical_json` is the **sorted-keys, no-whitespace** encoder already used for
  `profile_hash` (CES-0 §3) — same canonicalization → hash parity with the Polymer/R side. (Order is
  preserved inside each list — the hash binds the exact feature/sample ordering, which is what
  identifies the matrix.)
- Compute `size` = total bytes of (manifest + betas matrix); `checksums` = sha-256 over those bytes.
- Build `access_methods = (AccessMethod(type="file", access_url=<bundled betas path>),)`,
  `self_uri = f"drs://local/{uid}"`.
- Return the frozen `SEContractRef`.

The canonicalization + sha256 helpers should be **reused** from where CES-0 put them (the
`profile_hash` machinery in `analysis_profile.py`), not re-implemented — single source of truth for
the project's content-address discipline. If they are private, lift them to a small shared
`_hashing` helper as part of this slice.

---

## 5. Scope fences (what CES-1 does NOT do)

- **No grammar change** — `DataHandle.ref` stays `str`; no new grammar type or field.
- **No protocol change** — `run_cycle`, `verify_stage`, `drift_pass` untouched. Corpus stays 4.
- **No computation, no claim** — `exec_adapters.py`'s existing `dose_response` mean-diff path is
  untouched. CES-2 adds the methylation realizer that *consumes* `load_contract`.
- **No `run_cycle` wiring of `dimnames_hash`** — CES-1 produces the value; CES-2/CES-3 record it on
  `MaterializationContext` and wire it into drift. (The field already exists from CES-0.)
- **No served DRS endpoint, no refget digest** — DRS *shape* only; `refget_digest` is a noted slot.

---

## 6. Tests

Umbrella-only (`tests/`), pure/offline:

- **`SEContractRef` round-trips** — construct + `model_dump`/reload is identity; it is frozen.
- **`load_contract` returns the contract fields** — `contract_uid`, `assay == "beta"`,
  `genome_assembly == "hg38"`, `selection` present.
- **`dimnames_hash` is deterministic** — same fixture → same hash across calls; the `"sha256:"`
  prefix is present.
- **`dimnames_hash` is content-sensitive** — a unit test computes the hash for a permuted/edited
  feature- or sample-ID list and asserts it differs (guards against a constant/stub hash).
- **DRS shape present** — `access_methods` non-empty with a `file` method; `checksums` carries a
  `sha-256` digest; `self_uri` starts with `drs://`.
- **Unknown ref → `FileNotFoundError`** — and the message names the ref (matches `load_dataset`).
- **Fixture internal consistency** — `dim == [len(row_data), len(col_data)]`; the betas matrix has
  exactly `dim[0]` data rows and `dim[1]` value columns; every `col_data.Sample_Group ∈
  {TET2_mut, WT}`; feature IDs match the `cg########` format. (A guard so the fixture can't silently
  drift out of shape.)
- **Hash-parity canonicalization** — `dimnames_hash` uses the *same* canonical-json encoder as
  `profile_hash` (assert by computing an expected digest with the shared helper, not a hand-rolled
  one).

---

## 7. What CES-1 delivers vs defers

**Delivers (this phase, as its own plan):**
- `SEContractRef` (+ `AccessMethod`, `Checksum`) frozen umbrella models.
- The bundled `tet2_epicv2_demo` fixture: manifest JSON + sidecar betas TSV (EPICv2-shaped,
  synthetic values, a planted shift on a few probes for CES-2).
- `load_contract(ref) -> SEContractRef` + canonical `dimnames_hash` (reusing the CES-0 hash helper).
- Tests per §6; re-exports from the umbrella `__init__.py`.

**Defers:**
- **CES-2:** the local methylation realizer (`BorisLikeAdapter`) that reads the assay matrix and
  computes a scalar reduction; the two methodologically-independent legs; the licensing claim; and
  the **real-vs-public beta-value decision** parked here.
- **CES-3:** recording `dimnames_hash`/`profile_hash`/`semantic_run_id` on `MaterializationContext`
  through `run_cycle`; the drift-key wiring in `drift_pass`; the substrate→tier end-to-end.
- Live R-Engine adapter; `refget_digest`; served DRS endpoint; `QuantityVectorLeaf`.

---

## 8. Invariants preserved

- **Grammar domain-agnostic & unchanged;** `DataHandle.ref` stays a thin `str`.
- **Pure/deterministic, offline;** loader is `lru_cache`d stdlib I/O, like `load_dataset`.
- **Single content-address discipline** — `dimnames_hash` reuses the `profile_hash` canonicalization
  (hash parity by construction).
- **Back-compat** — purely additive; no existing call site changes; `check-all.sh` stays green
  (no grammar/protocol/viewer surface touched).
