# Phase 2.3 — wire the e-LOND gate into the live node

**Status:** Design / phase spec. v0.1
**Date:** 2026-06-13
**Author:** Z. Belden
**Anchor:** `docs/vision/2026-06-12-phase-2-north-star.md` (arc 1 → "alive"). Makes the Phase-2.1
4-way gate + Phase-2.2 defeat-refund actually RUN in a live node.
**Depends on:** Phase 2.1 (`evidence_map`, `run_cycle(evidence=)`, the `epicv2_casectrl_powered@1`
fixture), CES-4 (`NodeRunner` + the `content_address` opt-in flag + `tick`'s `RUN_CYCLE` branch that
threads `materializations=`).

**Decided this session:** a **separate** opt-in flag `evalue_gate` (not a reuse of
`content_address` — the two are orthogonal); **lazy-import** `evidence_map` inside `tick` to preserve
`node.py`'s numpy-free base import; **NodeRunner-only** scope (server/CLI exposure deferred).

---

## 0. Goal

The 4-way e-LOND licensing gate (`LICENSED ⇔ agreement ∧ SATISFIED ∧ grounded ∧ e-LOND-discovery`,
Phase 2.1) and the defeat-refund (Phase 2.2) are built and merged, but **dormant in production**:
`NodeRunner.tick` (`node.py:162`) calls `run_cycle` without `evidence=`, so a live node still licenses
on the 3-way gate. This slice threads `evidence_map(self.corpus)` into the live `run_cycle`, a
near-exact parallel to CES-4's `materialization_map` wiring, so the running node licenses under the
e-gate.

---

## 1. Architecture & boundaries

Umbrella-only (`src/polymer_claims/node.py`); grammar/protocol untouched; Corpus stays 4. Opt-in
behind a new flag, default off → byte-identical. **`node.py` must stay numpy-free at base import**
(CES-4 invariant): `materialization_map` is numpy-free so it is imported at the top, but
`evidence.py` imports numpy (`betting_evalue`) — so `evidence_map` is **lazily imported inside `tick`**
(only when `evalue_gate` is on). Verified today: `import polymer_claims.node` → numpy NOT in
`sys.modules`; this slice keeps that true.

---

## 2. The flag

`NodeRunner.__init__` and `from_seed` gain `evalue_gate: bool = False`, stored as `self.evalue_gate`.
It is **separate** from `content_address` (orthogonal concerns): `content_address` *records* the
dataset/apparatus content-address (`materialization_map`); `evalue_gate` *enforces* the e-LOND
licensing bar (`evidence_map`). A node may run either alone or both. Default `False` →
`evidence=None` → today's behavior.

---

## 3. The wiring (`tick`'s `RUN_CYCLE` branch)

Alongside the existing `mats` computation:

```python
if action is not None and action.kind == ActionKind.RUN_CYCLE:
    mats = (
        materialization_map(self.corpus, self.ctx, profiles=self.profiles)
        if self.content_address else None
    )
    if self.evalue_gate:
        from .evidence import evidence_map   # lazy: keeps node.py base import numpy-free
        ev = evidence_map(self.corpus)
    else:
        ev = None
    result = run_cycle(
        self.corpus, self.adapters, self.ctx,
        ledger=self.ledger, materializations=mats, evidence=ev,
        **self.run_cycle_kwargs,
    )
    ...
```

- `evidence_map` is recomputed each `RUN_CYCLE` tick (the corpus changes between ticks), exactly like
  `materialization_map`.
- An empty map (`{}` — no methyl-apparatus claims) is a no-op in VERIFY, so a non-methylation corpus is
  unaffected even with the flag on.
- `evalue_gate=False` → `evidence=None` → byte-identical to pre-2.3.

---

## 4. Data flow

`tick → [RUN_CYCLE: evidence_map(corpus) if evalue_gate] → run_cycle(evidence=ev) → VERIFY 4-way gate`.
Off → `evidence=None` → the e-discovery conjunct never fires → byte-identical.

---

## 5. Components & files

- **Modify `src/polymer_claims/node.py`** — `evalue_gate` param on `__init__`/`from_seed`;
  `self.evalue_gate`; the lazy `evidence_map` import + `evidence=ev` thread in `tick`'s `RUN_CYCLE`
  branch.
- **Modify `tests/conftest.py`** — the `methyl_node` helper gains an `evalue_gate` pass-through and a
  way to point at the well-powered fixture (so the e-gate licensing test has real power).
- **Tests** — `tests/test_node_content_address.py` (or a sibling): e-gate live (strong licenses, weak
  blocked), back-compat, numpy-free.

---

## 6. Testing

- **E-gate licenses live:** a `NodeRunner(evalue_gate=True)` over a one-claim corpus whose apparatus
  claim is the **well-powered** strong region (`epicv2_casectrl_powered@1`, region `cg00000001-05`)
  ticks to `LICENSED`, and `corpus.fdr_ledger.n_discoveries == 1` (the e-gate fired and passed).
- **E-gate blocks live (the money-shot in production):** the **weak** region (`cg00000006-10`,
  point estimate > 0.10 → SATISFIED, but e below the bar) over `evalue_gate=True` → stays **PENDING**
  (not LICENSED), `n_discoveries == 0`. The same claim with `evalue_gate=False` → LICENSES on the
  3-way gate (proving the e-gate is the only thing withholding it live).
- **Back-compat:** `evalue_gate=False` over the strong corpus → licenses as today; existing
  `test_node.py` / `test_node_content_address.py` byte-identical.
- **numpy-free base import:** `import polymer_claims.node` leaves `numpy` out of `sys.modules`
  (the lazy import is what guarantees this).
- `scripts/check-all.sh` ALL GREEN.

---

## 7. Scope fences & honesty

- **Delivers:** the `evalue_gate` flag + live wiring; the strong-licenses / weak-blocked e2e through
  the live runner; the numpy-free guard.
- **Defers:** exposing `evalue_gate` through `server.py`/`create_app`/the CLI `serve` command (a
  trivial follow-up, parallel to `content_address`'s server/CLI surface); auto-enabling the gate
  (stays opt-in). The synthetic-fixture caveat carries forward (the e-value addresses synthetic betas
  until the real-public-data swap).
- **Honesty:** this is plumbing — it does not change the e-value math or the gate logic (Phase
  2.1/2.2); it makes them fire in the live loop. The licensing demonstration requires the well-powered
  fixture (the strict e-LOND bar is real), exactly as in the Phase-2.1 static e2e.

---

## 8. Invariants preserved

- Grammar/protocol untouched; Corpus stays 4; `node.py` base import numpy-free (via the lazy
  `evidence_map` import).
- Opt-in / byte-identical default (`evalue_gate=False` → `evidence=None`).
- Determinism/purity unchanged (the e-value is deterministic given the data; the node is the existing
  impure driver).
