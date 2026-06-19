# Pre-Registration Ledger (Phase D, slice 1) — Design Spec

> **Date:** 2026-06-19 · **Status:** approved (design), pre-implementation
> **Scope:** pure-code grammar + protocol + tests (no external data; fully CI-gated)
> **Roadmap:** autonomous-hypothesis-loop §5a + Phase D · north-star §2(B)/(C) (e-value/FDR honesty core)
> **Predecessor machinery:** `grammar/src/polymer_grammar/fdr.py` (e-LOND), `protocol/.../verify.py` (the 3/4-way gate)

## 1. Goal

Close the **§5a selective-inference / multiplicity leak**. Today the e-LOND budget is charged at
**verify** (`verify.py:134-146`): only a hypothesis that survives to verify with an e-value ever advances
the test stream `t`. An autonomous agent can therefore generate many hypotheses, peek at the data, and
push only the winners to verify — so the multiplicity it fished across is never charged and the corpus
false-license rate `q` becomes a confident lie.

This slice makes a hypothesis **commit before it sees data**:
1. **Registration charges the budget.** A committed hypothesis advances the e-LOND `γ_t` slot at
   registration and **locks** its `α_t = q·γ_t·(D_{t-1}+1)` — *before* its e-value exists.
2. **Strict, no refund.** A registered hypothesis keeps its slot even if never executed or if it fails.
   Fishing across N hypotheses costs all N — the property that keeps `q` honest.
3. **Match-gate.** At verify, the executed claim's hypothesis content-hash must equal the one registered;
   any post-hoc change to region/criterion/levels is **REJECTED** (`HYPOTHESIS_ALTERED`), terminal.

## 2. Decisions (locked)

| Decision | Resolution |
|---|---|
| Where registration state lives | **Inside the existing `fdr_ledger`** — no 5th Corpus collection (Corpus stays exactly 4) |
| Charging model | **Charge at registration, strict, no refund** |
| Opt-in signal | **Presence of a pending registration entry** (`e_value is None`) for the claim in `fdr_ledger`. No registrations → byte-identical to today |
| Hypothesis identity | `commitment_hash(claim) = sha256(canonical_json(claim.evaluation_plan))` — captures region/graph + criterion + group levels |
| Integrity violation | `RejectionReason.HYPOTHESIS_ALTERED` (terminal, NOT reinstatable) |
| `fdr.py` ↔ `Claim` coupling | Kept apart: `fdr.py` stores a hash *string*; `commitment_hash(claim)` lives in a new `grammar/commitment.py` |

## 3. Grammar changes (pure)

### 3.1 `fdr.py` — `FDRTest` gains optional fields, two new ops

- `FDRTest.e_value: float | None` (was `float`, `ge=0.0`). `None` ⇒ **registered, unresolved**: its
  `alpha_allocated` (and `γ_t` slot) is locked, `discovery=False`.
- `FDRTest.commitment_hash: str | None = None` — the registered hypothesis hash.
- `register_test(ledger, claim_id, commitment_hash) -> FDRLedger`: append a pending `FDRTest` at
  `index = n_tests+1` with `alpha_allocated = target_fdr · γ_t · (n_discoveries+1)`, `e_value=None`,
  `discovery=False`, `commitment_hash=…`. Advances the stream immediately.
- `resolve_test(ledger, claim_id, e_value) -> FDRLedger`: find the **latest pending** entry for
  `claim_id` (`e_value is None`, `not retracted`); return a new ledger with that one entry replaced by a
  copy carrying `e_value` and `discovery = e_value >= 1/alpha_allocated` (against the **locked** α).
  Raises `ValueError` if there is no pending entry for `claim_id`.
- `n_discoveries`/`discoveries` are unchanged and already ignore pending entries (they filter
  `discovery and not retracted`).
- `process_test`/`process_stream`/`elond_decisions`/`retract_tests` are **unchanged** (the
  charge-at-verify path), so absent registration the behavior is byte-identical.

**Soundness under deferred / out-of-order resolution.** α is locked at registration using the discoveries
*known at that moment*. If earlier-registered tests are still pending when test `t` registers, `D_{t-1}`
is undercounted ⇒ `α_t` is **smaller** ⇒ strictly more conservative, so FDR ≤ `q` is preserved (locked α
is a safe lower bound on the ideal α). Registering then resolving in order reproduces standard e-LOND.

### 3.2 `commitment.py` (new) — hypothesis content hash

`commitment_hash(claim: Claim) -> str`: `"sha256:" + sha256(claim.evaluation_plan.model_dump_json()).hexdigest()`.
Deterministic (frozen models + tuple collections ⇒ canonical JSON). Two claims with the same plan hash
equal; any change to region probes, comparator, threshold, or group levels changes the hash.

### 3.3 `status.py` — one additive enum value

`RejectionReason.HYPOTHESIS_ALTERED = "hypothesis_altered"` (terminal; the protocol's reinstatement pass
must NOT treat it as reinstatable — only `DEFEAT_GROUNDED_OUT` reopens).

## 4. Protocol changes

### 4.1 REGISTER — `register_hypotheses(corpus, claim_ids=None) -> Corpus`

New pure function (`protocol/.../register.py`). For each id in `claim_ids` (default: all corpus claims
that carry an `evaluation_plan`), in **claim-id-sorted order** (deterministic), call
`register_test(ledger, id, commitment_hash(claim))`. Returns a new Corpus with the advanced
`fdr_ledger`. Idempotency guard: a claim that already has a **pending** registration is skipped (no
double-charge). Called **before** `run_cycle` (the commit-before-data step); for the autonomous loop the
agent registers at hypothesis-commit time, before pulling/executing the slice.

### 4.2 Match-gate + resolution in `verify_stage`

Augment the FDR block (`verify.py:134-146`). Before the existing charge-at-verify computation:
- `pending = {t.claim_id: t for t in corpus.fdr_ledger.tests if t.e_value is None and not t.retracted}`.
- For each executed claim `c` with an e-value AND `c.id in pending`:
  - **match-gate:** if `commitment_hash(c) != pending[c.id].commitment_hash` → mark `c` REJECTED with
    `rejection_reason=HYPOTHESIS_ALTERED` (does NOT resolve the ledger entry — the slot stays consumed,
    pending, never a discovery).
  - else → `ledger = resolve_test(ledger, c.id, e_value)`; record its discovery decision.
- The existing `already_tested` guard already excludes claims with a non-retracted ledger entry (a
  pending registration IS one), so registered claims never also hit the charge-at-verify
  `process_test` path. Non-registered claims are unaffected → byte-identical.
- `_e_ok(cid)` extends to consult resolved-registration decisions alongside `e_decisions`.

**No-refund invariant:** a registered claim that never executes (no exec record / no e-value) keeps its
pending entry across the cycle — slot consumed, not a discovery, not refunded.

## 5. What this does NOT change (invariants)

- **Corpus = exactly 4 collections.** Registration lives in `fdr_ledger`.
- **grammar/protocol stay pure + numpy-free.** `commitment_hash` uses stdlib `hashlib`/`json` only.
- **Additive/opt-in.** Every new field defaults so a no-registration run is byte-identical; the full
  existing suite (351 grammar + 363 protocol) must stay green unchanged.
- **One e-test per claim lifetime.** Registration is that one test; resolution fills it. Drift/defeat
  retraction still operates on resolved discoveries (`retract_tests`); pending entries are not
  discoveries, so retraction is a no-op on them (documented).

## 6. Out of scope (later Phase-D slices)

- §5a **literature**-shared-cause provenance (was the prior derived from an overlapping cohort) — overlaps
  North Star §E; needs the common-cause DAG.
- Multi-hypothesis **incubation / ranking**.
- A **require-registration-for-all** strict corpus mode (mirrors the adapter-registry's deferred strict
  mode) — this slice is per-claim opt-in.
- **Live-node / autonomous-agent wiring** (the agent that mass-registers before pulling data); this slice
  is the mechanism + tests, demonstrated via `run_cycle`.
- **Refund semantics** for registered-but-unexecuted hypotheses (deliberately excluded — strict).

## 7. Success criteria (what the tests must prove)

1. **Multiplicity is charged:** an e-value that is a discovery at `t=1` is **not** a discovery at `t=N`
   after N−1 prior registrations (the bar tightened by the locked α).
2. **Match-gate:** a claim whose plan was altered after registration is REJECTED with
   `HYPOTHESIS_ALTERED`; an unaltered claim resolves normally.
3. **Strict no-refund:** a registered-but-unexecuted hypothesis keeps its slot (the next registration's α
   reflects the consumed `t`).
4. **Soundness:** register-then-resolve in order == the discovery decision `process_test` would give for
   the same single test; out-of-order resolution is no less conservative.
5. **Byte-identical when off:** a `run_cycle` with no registrations is identical to today (existing suite
   green; a golden equality test on the resulting corpus/ledger).
6. **Corpus invariant:** still exactly 4 collections; grammar isolation + numpy-free import preserved.

## 8. Open implementation details (for the plan)

- Exact `evaluation_plan` JSON canonicalization (Pydantic `model_dump_json()` is already canonical for
  frozen models with tuple fields — confirm in Task 1).
- Whether `_e_ok` needs the resolved-registration decisions merged into `e_decisions` or a separate map.
- The integrate/reinstatement guard: confirm `HYPOTHESIS_ALTERED` is excluded from the reinstatement
  pass (only `DEFEAT_GROUNDED_OUT` reopens).
