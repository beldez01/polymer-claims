# CES-3 — content-address completeness: record it, then drift on it

**Status:** Design / phase spec. v0.1
**Date:** 2026-06-12
**Author:** Z. Belden
**Depends on:** CES-0 (the `MaterializationContext` fields `semantic_run_id`/`profile_hash`/
`dimnames_hash` already exist; `content_hash`, `profile_oracle_id`), CES-1 (`load_contract` →
`dimnames_hash`, the shared `canonical_sha256`), CES-2 (`region_delta_beta_claim`, the methylation
adapters, `CANONICAL_EPICV2_V1`). Slice CES-3 of the CES decomposition — the **fully-pinned** leg of
the credibility arc.
**Decided this session:** approach A (a pre-stamped per-claim **materialization map** passed into
`run_cycle`, all content-address computation umbrella-side; protocol does a pure dict lookup);
drift tightens **only when the content-address fields are present** (back-compat); a **static** test,
not live-`serve` wiring.

---

## 0. Goal

Today a licensed claim's `Satisfaction.materialization` is the single cycle-level `ctx` shared by
every claim (`grammar/evaluate.py:404` mints `Satisfaction(materialization=ctx)`; `execute.py:52`
passes the same `ctx` to every `verify`). So a license records *which API/data version* but not
*which exact dataset (by content) under which exact apparatus (by content)*. CES-3 closes that:

1. **Record** — a licensed claim's materialization carries its `dimnames_hash` (the SE-Contract
   content-address, CES-1), its `profile_hash` (the apparatus content-address, CES-0), and the
   composite `semantic_run_id` — so "licensed" means *"this tool, under this pinned profile P (by
   hash), over this dataset D (by content), beat θ"*, fully pinned.
2. **Drift on it** — DRIFT re-opens a licensed claim when its data (`dimnames_hash`) or apparatus
   (`profile_hash`) content-address moves, not only when a coarse `data_version` string changes.

This is the gap the CES audit named: the SemanticRunID/content-address was computable but never
recorded on the claim, so a license "silently inherits the gap." CES-3 records it and makes drift act
on it.

---

## 1. Architecture & boundaries

The content-address is **impure** to compute (`load_contract` reads the SE-Contract;
`content_hash` reads the profile). The recording point (`verify` → `Satisfaction.materialization`)
is in the **pure** protocol core. Approach A keeps the split clean:

- **Umbrella (impure):** a `materialization_map(corpus, base_ctx, *, profiles)` helper computes, for
  each executable claim, an enriched `MaterializationContext` (the base ctx + the three
  content-address fields), returning `dict[claim_id, MaterializationContext]`. All file/profile I/O
  lives here.
- **Protocol (pure, two additive params):** `execute_ground` and `run_cycle` gain an optional
  `materializations: dict[str, MaterializationContext] | None = None`. `execute_ground` uses
  `materializations.get(c.id, ctx)` as that claim's ctx for `verify` — **a pure dict lookup, no I/O**.
  `run_cycle` threads it through. Default `None` → today's behavior, **byte-identical**.
- **Drift (pure, predicate change):** `drift._is_fresh` additionally compares `profile_hash` and
  `dimnames_hash` **when the recorded materialization carries them** (tighten-only; absent → today's
  `api/data_version` check).
- **Grammar:** **untouched** — the three `MaterializationContext` fields already exist (CES-0). Corpus
  stays 4.

This mirrors the existing injection pattern (adapters/oracles are passed in; here a pre-computed map
is passed in) and preserves protocol purity + determinism.

---

## 2. The umbrella materialization map

New `src/polymer_claims/materialization.py`:

```python
def materialization_map(
    corpus, base_ctx, *, profiles=(CANONICAL_EPICV2_V1,)
) -> dict[str, MaterializationContext]:
    ...
```

For each claim that has an `evaluation_plan` whose terminal node carries a `DataHandle` input and an
`oracle_ref`:

- **`dimnames_hash`** = `load_contract(handle.ref).dimnames_hash` (CES-1). A `ref` that does not
  resolve (no bundled contract) → skip the claim (no enriched entry; it keeps the base ctx).
- **`profile_hash`** = `content_hash(profile)` for the profile whose `profile_oracle_id(profile)`
  equals the node's `oracle_ref` (resolved from the passed-in `profiles` tuple). An `oracle_ref` with
  no matching profile → `profile_hash=None` (records the dataset address but not an apparatus one).
- **`semantic_run_id`** = `canonical_sha256({"tool": node.impl, "param_signature":
  <canonical of node.params>, "input_signature": <canonical of the inputs' dimnames_hashes>,
  "profile_hash": profile_hash})` — the CES-0 §3 composite `SHA256(tool · params · inputs ·
  profile_hash)`, computed with the shared `canonical_sha256` (hash parity).
- The enriched ctx = a fresh `MaterializationContext` copying `base_ctx`'s
  `id`/`api_version`/`data_version`/`note` and adding the three fields (constructed fresh, not
  `model_copy`, so it is fully validated).

The helper is **pure-given-its-inputs** apart from `load_contract`'s bundled-file read — exactly the
CES-1/CES-2 impurity boundary. It is **not** re-exported in a way that pulls numpy into the base
import (it imports no numpy).

---

## 3. The protocol seam (additive)

- **`execute_ground(corpus, adapters, ctx, only=None, materializations=None)`** — in the claim loop:
  `ctx_c = materializations.get(c.id, ctx) if materializations else ctx`; call
  `verify(c.evaluation_plan, ctx_c, adapters, claim_leaves=c.leaves)`. Nothing else changes; the
  minted `Satisfaction.materialization` is now the per-claim enriched ctx for content-addressed
  claims, and the shared `ctx` for everything else.
- **`run_cycle(..., materializations=None)`** — a new keyword-only param threaded straight to
  `execute_ground`. No other stage sees it.
- **Back-compat:** `materializations=None` (or a claim absent from the map) → the exact current
  behavior; all existing execute/cycle tests stay green by construction.

---

## 4. The drift predicate (tighten-only-when-present)

`drift._is_fresh(claim, current)` today: fresh iff ANY satisfaction materialization matches `current`
on `api_version` AND `data_version`. CES-3 extends the per-satisfaction match:

```
matches(m, current) :=
    m.api_version == current.api_version
    and m.data_version == current.data_version
    and (m.profile_hash is None  or m.profile_hash  == current.profile_hash)
    and (m.dimnames_hash is None or m.dimnames_hash == current.dimnames_hash)
```

So a claim licensed *with* a content-address is fresh only if the apparatus **and** the dataset
content-addresses still match; a claim licensed *without* them (const-plan, pre-CES-3) is judged
exactly as today. `reopen_drifted` is unchanged — a drifted content-addressed claim re-opens to
PENDING with `MATERIALIZATION_DRIFTED`, as for any drift. (`semantic_run_id` is the recorded
composite for the reproducibility audit trail; the drift key is the two granular components so a
finding can say *what* moved.)

---

## 5. Tests

**Protocol** (`protocol/tests/`):
- `execute_ground`/`run_cycle` with a `materializations` map stamps the per-claim ctx onto the minted
  `Satisfaction.materialization` (a two-claim corpus where each claim gets a distinct enriched ctx →
  each Satisfaction carries its own `dimnames_hash`/`profile_hash`); without the map, byte-identical.
- `drift._is_fresh`: a claim whose recorded materialization has `profile_hash`/`dimnames_hash` is
  **stale** when `current`'s differ (each independently), **fresh** when both match; a claim with the
  fields absent is judged on `api/data_version` only (existing drift tests stay green).
- `drift_pass` + `reopen_drifted` end-to-end: a content-addressed LICENSED claim re-opens to PENDING
  (`MATERIALIZATION_DRIFTED`) when the current `dimnames_hash` moves.

**Umbrella** (`tests/`):
- `materialization_map` computes `dimnames_hash` (== `load_contract(ref).dimnames_hash`),
  `profile_hash` (== `content_hash(CANONICAL_EPICV2_V1)`), and a deterministic `semantic_run_id`
  (== the shared `canonical_sha256` recipe over tool/params/inputs/profile_hash); a claim with an
  unresolvable ref or no oracle match degrades gracefully (skip / `profile_hash=None`).
- **End-to-end (the deliverable):** run the CES-2 methylation claim through `run_cycle` *with*
  `materialization_map(...)`; assert the LICENSED claim's `Satisfaction.materialization` now carries
  the full content-address (`dimnames_hash`/`profile_hash`/`semantic_run_id` all set); then
  `drift_pass` against a `current` ctx with a changed `dimnames_hash` flags it, and `reopen_drifted`
  re-opens it to PENDING.
- `check-all.sh` ALL GREEN (grammar/viewer untouched; protocol additive).

---

## 6. Scope fences & honesty

- **Static only** — `materialization_map` is wired into a test, not into the live `NodeRunner`/`serve`
  loop (a later enrichment; the seam is ready when wanted).
- **Two additive protocol params + one predicate change; grammar untouched; Corpus stays 4.** No
  stage other than `execute_ground` reads `materializations`.
- **`semantic_run_id` is the Python-side composite.** CES-0 already flags that full Python/R hash
  parity needs a golden-hash fixture against the live R serializer before any R-side code relies on
  the digest; CES-3 records the Python digest deterministically (all this slice needs), and does NOT
  claim validated R parity.
- **Synthetic-data caveat carries forward** (CES-2): the content-address is real and complete, but it
  addresses synthetic betas until the real-public-data swap.
- **`profiles` resolution is explicit** — the map resolves `oracle_ref` against a passed-in `profiles`
  tuple (default the canonical profile); a full oracle-id→profile registry is deferred (YAGNI for one
  profile).

---

## 7. What CES-3 delivers vs defers

**Delivers:** `materialization_map` (umbrella); the `materializations=` seam on
`execute_ground`/`run_cycle` (protocol, additive); the tightened `_is_fresh` drift predicate; the
tests + the end-to-end (license records the full content-address → drift re-opens on a data/apparatus
move).

**Defers:** live `serve`/`NodeRunner` wiring of the map; the oracle-id→profile registry; validated
Python/R hash parity (golden fixture); the real-public-data swap (CES-2 caveat). These do not block
CES-3.

---

## 8. Invariants preserved

- **Grammar untouched; protocol purity intact** — `materializations` is a pre-computed dict the core
  only reads; all I/O stays umbrella-side. Determinism preserved.
- **Back-compat** — `materializations=None` and the absent-fields drift fallback keep every existing
  test byte-identical; only content-addressed claims gain the stricter behavior.
- **Content-address completeness** — a license now pins the design formula + Layer-C internals (via
  `profile_hash`) AND the exact dataset (via `dimnames_hash`) that the SemanticRunID missed; drift
  acts on both.
