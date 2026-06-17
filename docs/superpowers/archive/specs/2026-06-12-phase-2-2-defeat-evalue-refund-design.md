# Phase 2.2 — defeat-as-e-value-update + alpha-wealth refund

**Status:** Design / phase spec. v0.1
**Date:** 2026-06-12
**Author:** Z. Belden
**Anchor:** `docs/vision/2026-06-12-phase-2-north-star.md` §2(B) — the "one mechanism" climax of Phase 2
arc 1. Builds directly on Phase 2.1 (the e-LOND ledger now advances in VERIFY; `betting_evalue`;
`evidence_map`).
**Depends on:** Phase 2.1 (`grammar/fdr.py` e-LOND; VERIFY owns the ledger), the defeat layer
(`grammar/defeat.py` `grounded_extension`/`effective_defeats`), AGM (`grammar/revision.py`
`restore_consistency` → `RevisionResult.flipped_out` / `retraction.possibly_retracted`), and
`protocol/integrate.py`.

**Decided this session:** **contest → retraction** (reuse the proven grounded-extension / strength
contest as the "successful defeat" signal; the consequence is the new part) and **tombstone
live-discoveries** (mark the defeated claim's FDR test retracted; count live only; freeze the recorded
α). NOT a literal per-attack e-value combination, NOT an online α-recompute.

---

## 0. Goal

After Phase 2.1, VERIFY **adds** a discovery to the e-LOND ledger when a claim licenses, but nothing
ever **removes** it. A claim that is later defeated still consumes a discovery slot — the FDR
accounting goes stale, and "defeat" (grounded extension / AGM) and "FDR" (the ledger) remain two
separate subsystems. Worse, the de-license itself is incomplete: a previously-LICENSED claim that a
new attacker grounds-OUT today **keeps `status=LICENSED`** — VERIFY only re-flips claims executed
*this* cycle (`verify.py`), and INTEGRATE only *removes* AGM-incompatible claims (`integrate.py:38`
returns `rr.claims` with grounded-OUT non-AGM statuses unchanged). The status field lags grounded
membership.

This slice closes both: a successful defeat **de-licenses** the claim (flips its status) **and
refunds** its discovery (tombstones the ledger entry). A de-license now flows *through* the ledger, so
**`LICENSED ⇒ a live e-LOND discovery`** becomes an invariant and defeat/licensing/FDR are one
threshold-crossing. The "downward e-value update" is realized as the discovery tombstone (effective
e-value → below bar); the defeat *decision* reuses the existing grounded/Pareto contest — we do not
fabricate a per-attack e-value.

---

## 1. Architecture & boundaries

Entirely **pure** (grammar + protocol): the tombstone is a pure ledger transform; the defeat detection
is the existing pure `restore_consistency`/grounded machinery. No I/O, clock, or randomness; numpy-free.
Corpus stays 4; `FDRLedger` keeps its name (one bool field added). VERIFY = licensing/**add**;
INTEGRATE = defeat-reconciliation/**retract** — symmetric, well-separated operations on the one ledger.

---

## 2. Grammar (`grammar/src/polymer_grammar/fdr.py`) — the tombstone

- **`FDRTest`** gains `retracted: bool = False`.
- **Live-discovery counts:** `n_discoveries`, `discoveries`, and `is_discovery` count a test only when
  `t.discovery and not t.retracted`.
- **New `retract_tests(ledger, claim_ids) -> FDRLedger`** (pure, immutable): returns a new ledger in
  which every `FDRTest` whose `claim_id ∈ claim_ids` has `retracted=True` (others unchanged). Marking a
  non-discovery test retracted is harmless (it was never counted). The recorded `alpha_allocated` and
  `e_value` are **frozen** at test-time — never re-derived.
- **Validity stance (the tombstone choice):** past α allocations are not recomputed. A subsequent
  `process_test` reads the now-lower **live** `n_discoveries`, so future α reflects only live
  discoveries — the budget a defeated discovery earned is clawed back going forward. The full **online
  α-recompute** (re-deriving every prior test's α as if the retraction had always held) and its
  anytime-valid-FDR proof under retroactive un-rejection are the documented **frontier** (North Star
  §2(B)), deferred.

---

## 3. Protocol (`protocol/src/polymer_protocol/integrate.py`) — defeat de-licenses + refunds

INTEGRATE already merges derived rebut edges, runs `restore_consistency` (AGM), and has
`rr.flipped_out` (claims that left the grounded extension this cycle, relative to
`scaffolding.grounded_extension`) and `rr.retraction.possibly_retracted` (the AGM-removed set). Add,
after `restore_consistency`:

```python
# defeated this cycle: LICENSED survivors grounded-OUT, plus AGM-removed claims.
defeated_licensed = {
    c.id for c in rr.claims if c.id in rr.flipped_out and c.status == Status.LICENSED
}
removed = rr.retraction.possibly_retracted if rr.retraction is not None else frozenset()
retract_ids = frozenset(defeated_licensed) | removed

# de-license the grounded-OUT survivors (mirrors VERIFY's grounded-OUT -> REJECTED rule).
new_claims = tuple(
    _reject(c) if c.id in defeated_licensed else c
    for c in rr.claims
)
new_ledger = retract_tests(corpus.fdr_ledger, retract_ids)

new_corpus = corpus.model_copy(
    update={"claims": new_claims, "defeat_edges": rr.edges, "fdr_ledger": new_ledger}
)
```

- **`_reject(c)`** mirrors VERIFY's grounded-OUT path: `status=REJECTED`, `licensing=None`,
  `pending_reason=None`, re-validated via `Claim.model_validate(c.model_copy(update=...).model_dump())`
  (a bare `model_copy` skips validators). REJECTED (not PENDING) keeps it consistent with `verify.py`'s
  existing `c.id not in in_ext -> REJECTED` rule.
- **Within a cycle:** VERIFY adds a discovery for a claim that licenses; if a co-occurring undefeated
  attacker grounds it OUT, INTEGRATE retracts that same discovery and rejects it — net: not a live
  discovery. The credit snapshot is already taken post-INTEGRATE (`cycle.py`), so this is consistent.
- **Back-compat:** no defeat → `flipped_out` empty and `possibly_retracted` empty →
  `retract_tests(ledger, ∅)` returns the ledger unchanged and no claim flips → byte-identical to today.

---

## 4. Data flow (one cycle)

```
… → VERIFY[ e-LOND ADDS discoveries; 4-way gate ] → INTEGRATE[ AGM + defeat-de-license + retract_tests REFUND ]
```

No defeat this cycle → INTEGRATE's new block is a no-op → pre-2.2 behavior byte-identical.

---

## 5. Components & files

- **Modify `grammar/src/polymer_grammar/fdr.py`** — `FDRTest.retracted`; live-discovery counts; add
  `retract_tests`. Export `retract_tests` from `grammar/__init__.py`.
- **Modify `protocol/src/polymer_protocol/integrate.py`** — the defeat-de-license + refund block; a
  `_reject` helper; thread the new ledger into the returned corpus.
- **Tests** — grammar `fdr` (retracted counts + `retract_tests`); protocol `integrate` (de-license +
  refund + back-compat) + the e2e money-shot.

---

## 6. Testing

**Grammar (`grammar/tests/`):**
- `retracted=True` excludes a test from `n_discoveries`/`discoveries`/`is_discovery`.
- `retract_tests(ledger, ids)` marks exactly the matching `claim_id`s, leaves others, is immutable.
- A `process_test` AFTER a retraction allocates α from the reduced live `n_discoveries` (the budget
  clawback): build a 2-discovery ledger, retract one, then `process_test` a third — its
  `alpha_allocated == target·γ_3·(1+1)` (live D=1), not `·(2+1)`.

**Protocol (`protocol/tests/`):**
- **De-license + refund:** a corpus with a LICENSED claim `A` that carries a live discovery, plus an
  undefeated attacker `B` and an effective defeat edge `B→A`; `integrate` grounds `A` OUT → `A.status
  == REJECTED`, `A.licensing is None`, and the ledger's test for `A` is `retracted` (`n_discoveries`
  drops by one).
- **AGM-removed refund:** an AGM-`INCOMPATIBLE_WITH`-retracted licensed claim is removed from the
  corpus AND its discovery is tombstoned.
- **Back-compat:** a corpus with no new defeats → `integrate` leaves claims + ledger byte-identical.

**End-to-end (the deliverable):** the same A/B setup driven so `A` first licenses with a discovery
(`n_discoveries==1`), then the attacker is present → `integrate` de-licenses `A` to REJECTED AND
`n_discoveries` goes 1→0 — proving the de-license flows through the ledger (defeat and FDR are one
mechanism). `scripts/check-all.sh` ALL GREEN.

---

## 7. Scope fences & honesty

- **Delivers:** `FDRTest.retracted` + `retract_tests` + live-discovery counts; defeat-driven
  de-license (fixes the latent LICENSED-grounded-OUT staleness); the ledger refund; the e2e.
- **Defers (documented):** **literal per-attack-kind e-value combination** (e.g. an undermine
  recomputing a lower support e-value — the deeper §2(B) fusion); **reinstatement** (un-tombstone +
  un-reject when an attacker is itself later defeated — v1 defeat is terminal); the **online
  α-recompute** of past tests + its anytime-valid-FDR proof; **drift-reopen tombstoning** (this slice is
  the *defeat* path; `reopen_drifted` tombstoning is a parallel follow-up).
- **Honesty:** the "downward e-value update" is realized as the discovery tombstone — we do **not**
  fabricate an e-value number; the defeat decision is the existing grounded/Pareto contest. The
  tombstone keeps past α frozen (the online refund is frontier). **Back-compat risk:** flipping
  grounded-OUT LICENSED→REJECTED is *new* behavior — any existing test relying on a LICENSED-but-
  grounded-OUT claim staying LICENSED must be migrated (the new behavior is the correct one; the old
  was a latent staleness bug).

---

## 8. Invariants preserved

- **Purity:** grammar/protocol stay pure/deterministic; tombstoning + grounded detection are pure;
  numpy-free. Corpus stays 4; `FDRLedger` entity kept (one bool added).
- **New invariant:** `LICENSED ⇒ a live e-LOND discovery` holds after INTEGRATE — defeat, licensing,
  and FDR are one threshold-crossing.
- **Back-compat:** no-defeat cycles are byte-identical; only a claim that is actually defeated gains
  the de-license + refund.
