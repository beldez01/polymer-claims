# V2.0 — Evidence-licensed external capability cell (generalization test)

**Date:** 2026-06-29
**Author:** Z. Belden (synthesized with Claude)
**Status:** DESIGN — awaiting review → `writing-plans`
**Roadmap item:** V2.0 (`docs/superpowers/2026-06-23-remaining-roadmap.md`, "Vision-derived additions")
**Depends on:** Capability Cell + Registry V1 (merged `b058d3c`, 2026-06-27)

---

## 1. Purpose

V1 shipped the `CapabilityCell` + `CapabilityRegistry` and registered the three existing
reductions (`stats::mean_diff`, `methyl::region_delta_beta`, `methyl::n_dmps`) as the first cells.
The roadmap's V2.0 is the **generalization test**: register **one** genuinely-new capability —
*not* a re-expression of an existing reduction — specifically to discover **where the V1 abstraction
does not fit**. What this slice teaches gates the V2.1–V2.3 menu fan-out and the vision's closed-world
agent execution.

This spec registers an **external-model, evidence-licensed** capability. It is the sharpest
generalization test because all three V1 cells share one hidden shape — *Quantity → threshold →
categorical, licensed by exactly two independent pure-Python recompute legs* — and an
external/evidence-backed capability breaks precisely that shape.

**Non-goal:** this is not the wedge (H1.A2 → H2 stays the critical path), not closed-world
*enforcement*, and not a menu fan-out. One capability, one minimal principled extension, one lesson.

---

## 2. The misfit V1 cannot express (verified against the code)

Attempting to register the existing BioNeMo evidence pattern (`examples/bionemo_plumbing/run.py`) as
a `CapabilityCell` fails on concrete, load-bearing points:

| V1 site | What breaks |
|---|---|
| `grammar/.../capability.py` `min_executing_adapters` (fixed `== 2`) | An external/cached single call has **one** real adapter. V1 *mandates* exactly two. |
| `eligible_adapter_identities` + `adapters_independent()` (`protocol/.../adapter_registry.py`) | The "air-gap" today is **a recompute model** (two legs, different owner + `implementation_hash`). The BioNeMo example fakes it: a `SyntheticCorroboratorAdapter` that **echoes the same cassette score** → independence is a *registry-attested fiction*, not a real air-gap. |
| `oracle: OracleRequirement` (`default_oracle_id`, `required`) | Only caps validation tier. There is **no field** to bind the e-value calibration that actually licenses an evidence claim. |
| Evidence licensing (`src/polymer_claims/evidence.py` `evidence_map`/`betting_evalue`) | Lives **orthogonal** to the cell; the betting e-value assumes a **stream**, so it does not transfer to a single call. |

**The single lesson:** licensing has (at least) two modes. A capability cell must **name its
licensing mode**; "two-way recompute air-gap" is one mode, not a universal law.

---

## 3. The capability

Register one cell:

- **`capability_id`:** `bionemo::nim_property`
- **`capability_version`:** `v1`
- **`operation_impl`:** `bionemo::nim_property`
- **Vehicle:** the existing **neutral external-model score** (the `cassette.json` mechanism in
  `examples/bionemo_plumbing/`). The subject matter is *deliberately neutral* — the example itself
  calls it a "deferred-wedge: neutral plumbing score." The teaching payload is the **licensing mode**,
  not biology, so we make no biological claim.
- **Produces:** a `quantity` node output (`ProducedLeafSpec(leaf_kind="quantity", ...)`) with a
  `categorical` claim leaf — the **same convention as the three existing cells** (`produced=_Q`,
  `claim_leaf_kinds=("categorical",)`); no new output-typing work.
- **Adapters:** **one** external adapter (`bionemo-nim`, the cached `BioNeMoNIMAdapter`). No synthetic
  corroborator.
- **Licensing mode:** `evidence_single` (see §4).

This is real per the vision's "Start Narrow" bar: schema + fixtures (`cassette.json` + an oracle
dossier) + typed outputs + comparison rule + ≥1 adapter + verifiable artifacts.

---

## 4. Honest licensing semantics — `evidence_single`

A single external score must earn an honest e-value (the epistemic core is e-value-native; the
e-LOND ledger licenses claims under arbitrary dependence). The construction is a **single-observation
likelihood-ratio e-value sourced from the bound oracle dossier**:

1. The cell binds an **oracle dossier** that supplies a **null reference** for the score. The dossier
   already carries `anchor` and `relative_uncertainty`; for `evidence_single` these (plus a small
   `evidence_null` descriptor if needed — §5) define a null distribution `L_null` and an alternative
   `L_alt` for the score.
2. The observed external score `s` yields a **one-shot e-value**
   `e = clip( L_alt(s) / L_null(s) )` — a likelihood ratio is a valid e-value (`E_H0[e] ≤ 1`); the clip
   keeps it a proper test supermartingale increment.
3. `e` feeds the **existing e-LOND / FDR ledger** exactly like any other test. The claim licenses iff
   `e` clears the e-LOND threshold; otherwise it stays **PENDING** (never silently licensed).
4. **Trust basis, stated truthfully:** oracle calibration (the null) + attestation (the cached call's
   provenance) + the e-value clearing the threshold. **No second adapter; no `independence_witnessed`
   claim** for this mode.

This simultaneously closes the "oracle only caps tier" gap: for `evidence_single` cells the **oracle
dossier *is* the e-value calibration source**.

> **Honesty note.** The certificate for an `evidence_single` claim MUST NOT assert air-gap
> independence. `build_certificate` currently sets `independence_witnessed=True` from a forwarded
> registry; for this mode it records the evidence/oracle basis instead. Enshrining the
> synthetic-corroborator fiction in a *registered* cell is explicitly rejected.

---

## 5. Minimal V1 → V2 schema delta (additive; byte-identical when off)

All changes are additive and default to current behavior, so the three existing cells and every
existing suite are **byte-identical**.

**Grammar layer — `grammar/src/polymer_grammar/capability.py`:**

- Add `licensing_mode: Literal["recompute_x2", "evidence_single"] = "recompute_x2"` to
  `CapabilityCell`. The default preserves the three existing cells exactly.
- Relax the `min_executing_adapters` invariant:
  - `recompute_x2` → must be `== 2` (unchanged).
  - `evidence_single` → must be `== 1`.
- Make the existing `oracle` field load-bearing for `evidence_single` (`required=True` enforced for
  that mode). Add an optional `evidence_null` descriptor **only if** the dossier's `anchor` +
  `relative_uncertainty` are insufficient to define `L_null`/`L_alt` (decide during planning; prefer
  reusing the dossier).
- `validate_claim_shape` gains an `evidence_single` branch:
  - adapter-count expectation keyed off `licensing_mode` (1 for `evidence_single`, 2 for
    `recompute_x2`);
  - oracle-required enforced for `evidence_single`;
  - the `recompute_x2` path and all existing output-type / leaf-kind checks are untouched.

**Umbrella layer:**

- A small evidence function: `(score, null-calibration) → e-value` (the §4 likelihood ratio). Sits
  beside the existing `evidence.py`; numpy-free (pure arithmetic), so base import stays clean.
- `src/polymer_claims/capabilities.py`: register `NIM_PROPERTY_CELL` (the fourth cell) with
  `licensing_mode="evidence_single"`, `min_executing_adapters=1`, the `bionemo-nim` adapter identity,
  and the bound oracle.
- Wire the `evidence_single` e-value into the e-LOND licensing path (route through the existing
  e-value/e-LOND test rather than the two-adapter `run_cycle` air-gap path).
- `build_certificate`: for `evidence_single`, emit the honest evidence/oracle basis; do **not** set
  `independence_witnessed`.

**Invariants preserved:** `grammar/` + `protocol/` stay pure + numpy-free; `Corpus` stays exactly 4
collections; new fields are `X | None = None` / defaulted with present-only-when-relevant validators;
numpy (if any) stays behind `[embed]`.

---

## 6. Fixtures, tests, conformance

**Fixtures**

- Reuse `examples/bionemo_plumbing/cassette.json` (the cached external score).
- An oracle dossier carrying the null calibration for the score.

**Tests** (TDD; failing test first)

1. **Conformance positive** — the `evidence_single` cell + its claim pass `validate_claim_shape`
   (adapter count 1, oracle required present).
2. **Conformance negative** — a `recompute_x2` cell with one adapter, and an `evidence_single` cell
   missing its oracle, each produce the right `ConformanceReason`.
3. **Honest license** — single cached `bionemo-nim` adapter + a supra-threshold e-value → LICENSED via
   e-LOND; the certificate records the evidence/oracle basis and **not** `independence_witnessed`.
4. **Honest non-license** — a sub-threshold e-value → PENDING (not licensed).
5. **Byte-identical regression** — the three `recompute_x2` cells, all existing capability tests, and
   the full umbrella/grammar/protocol suites are unchanged.

**Honesty cleanup**

- Remove the synthetic-corroborator path from the *registered-cell* licensing route. The
  `examples/bionemo_plumbing/` two-adapter demo may remain as a historical example, but the registered
  capability does not depend on it. (Confirm during planning whether the example is updated or left as
  a labeled legacy artifact.)

---

## 7. Acceptance criteria

1. A fourth cell `bionemo::nim_property@v1` is registered with `licensing_mode="evidence_single"` and
   `min_executing_adapters=1`.
2. It licenses a claim **offline** from the cached cassette via a single adapter and an honest
   e-LOND-gated e-value — with **no** synthetic corroborator and **no** air-gap independence claim.
3. The bound oracle dossier is the e-value calibration source (the V1 "oracle only caps tier" gap is
   closed for this mode).
4. `validate_claim_shape` correctly accepts/rejects both licensing modes.
5. The three existing cells and all existing suites are byte-identical; `grammar/` + `protocol/` stay
   pure + numpy-free; `scripts/check-all.sh` is green.
6. The design doc records the discovered misfit and the licensing-mode lesson (input to V2.1–V2.3).

---

## 8. What this explicitly does NOT do (parked)

- Closed-world **enforcement** (refusing non-conformant claims at the gate) — deliberately separate.
- The V2.1–V2.3 menu fan-out — gated on this slice's teaching.
- A *real* biological NIM operation / real cassette — the neutral score is the chosen vehicle.
- Any networked NIM call — cached/offline only.
- A general calibration framework — only the minimal single-observation likelihood-ratio e-value.

---

## 9. Rhythm

`writing-plans` → `superpowers:subagent-driven-development` (TDD per task) → whole-branch review →
merge `--no-ff` → update `CONTINUE.md` + memory.
