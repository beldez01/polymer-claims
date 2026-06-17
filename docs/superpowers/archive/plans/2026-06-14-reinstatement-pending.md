# Reinstatement → PENDING Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax
> for tracking.

**Goal:** When an attacker is itself defeated, reopen the defeat-rejected claim it knocked out to PENDING
so it re-tests on current data (the symmetric counterpart to Phase 2.2's defeat-as-de-license).

**Architecture:** A grammar `RejectionReason` enum records *why* a claim was REJECTED (`Claim.rejection_reason`,
one-directional validator); the protocol stamps the cause at each rejection site and adds a reinstatement
block in INTEGRATE mirroring the Phase-2.2 `flipped_out` block — `flipped_in ∧ REJECTED ∧ DEFEAT_GROUNDED_OUT
∧ has-plan → reopen to PENDING`. Re-test, never auto-relicense. grammar/protocol stay pure + numpy-free;
Corpus = 4.

**Tech Stack:** Python 3.12, pydantic v2 (frozen `_Model`), `uv` + `pytest` + `ruff`. Spec:
`docs/superpowers/archive/specs/2026-06-14-reinstatement-pending-design.md`.

## File structure

- `grammar/src/polymer_grammar/status.py` — **modify**: `RejectionReason` enum + `PendingReason.REINSTATED`.
- `grammar/src/polymer_grammar/claim.py` — **modify**: `Claim.rejection_reason` field + validator.
- `grammar/src/polymer_grammar/__init__.py` — **modify**: export `RejectionReason`.
- `grammar/tests/test_rejection_reason.py` — **create**: grammar unit tests.
- `protocol/src/polymer_protocol/verify.py` — **modify**: split the rejection branch (stamp REFUTED / DEFEAT_GROUNDED_OUT).
- `protocol/tests/test_verify.py` — **modify**: add two stamping tests.
- `protocol/src/polymer_protocol/integrate.py` — **modify**: stamp DEFEAT_GROUNDED_OUT in `_reject`; add `_reinstate` + the reinstatement block.
- `protocol/tests/test_integrate.py` — **modify**: defeat-stamp + reinstatement + refuted-guard + no-plan-guard tests.
- `docs/superpowers/CONTINUE.md` — **modify** (final task).

**Note (scope):** `RejectionReason.ROBUSTLY_BLAMED` is defined for completeness but **not stamped** in
this slice — `grammar/.../blame.py:duhem_status` has **no consumer in `protocol/src`** (verified), so
there is no live REJECTED-by-robust-blame site to stamp. Reinstatement keys only on `DEFEAT_GROUNDED_OUT`,
so this is safe; wiring + stamping robust-blame is a future slice.

---

### Task 1: Grammar — `RejectionReason` + `PendingReason.REINSTATED` + `Claim.rejection_reason`

**Files:**
- Modify: `grammar/src/polymer_grammar/status.py`, `grammar/src/polymer_grammar/claim.py`, `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_rejection_reason.py`

- [ ] **Step 1: Write the failing test**

Create `grammar/tests/test_rejection_reason.py`:

```python
from __future__ import annotations

import pytest

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    PatternRef,
    PendingReason,
    RejectionReason,
    Status,
)


def _claim(status, **extra):
    return Claim(
        id="x", title="x", pattern=PatternRef(id="p", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="t"),), status=status, **extra,
    )


def test_rejection_reason_values():
    assert {r.value for r in RejectionReason} == {
        "defeat_grounded_out", "refuted", "robustly_blamed",
    }


def test_pending_reason_reinstated_exists():
    assert PendingReason.REINSTATED.value == "reinstated"


def test_rejected_claim_accepts_rejection_reason():
    c = _claim(Status.REJECTED, rejection_reason=RejectionReason.DEFEAT_GROUNDED_OUT)
    assert c.rejection_reason is RejectionReason.DEFEAT_GROUNDED_OUT


def test_rejected_claim_allows_none_reason_backcompat():
    c = _claim(Status.REJECTED)
    assert c.rejection_reason is None


def test_non_rejected_claim_rejects_rejection_reason():
    with pytest.raises(ValueError, match="only valid when status=REJECTED"):
        _claim(Status.CONJECTURED, rejection_reason=RejectionReason.REFUTED)


def test_pending_with_reinstated_reason_validates():
    c = _claim(Status.PENDING, pending_reason=PendingReason.REINSTATED)
    assert c.pending_reason is PendingReason.REINSTATED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_rejection_reason.py -q`
Expected: FAIL with `ImportError: cannot import name 'RejectionReason'`.

- [ ] **Step 3: Add the enums**

In `grammar/src/polymer_grammar/status.py`, add `REINSTATED` to `PendingReason` (after the
`ADAPTER_NOT_INDEPENDENT` line) and add the new enum at the end of the file:

```python
    # a defeat-rejected claim whose attacker was itself defeated: reopened to re-test (reinstatement)
    REINSTATED = "reinstated"


class RejectionReason(str, Enum):
    """Why a claim is REJECTED (symmetric to PendingReason). The protocol decides which causes are
    reinstatable; only DEFEAT_GROUNDED_OUT is (its attacker may later fall)."""

    DEFEAT_GROUNDED_OUT = "defeat_grounded_out"   # knocked out of the grounded extension by an attacker
    REFUTED = "refuted"                           # the data refuted it (terminal)
    ROBUSTLY_BLAMED = "robustly_blamed"           # Duhem robust blame (terminal; reserved, not yet wired)
```

(Place `REINSTATED` as the last member of `PendingReason`; place `RejectionReason` as a new top-level
class below it.)

- [ ] **Step 4: Add the field + validator to `Claim`**

In `grammar/src/polymer_grammar/claim.py`:
(a) Change the status import (line 24) to include `RejectionReason`:
```python
from .status import PendingReason, RejectionReason, Status
```
(b) Add the field directly after `pending_reason` (line 36):
```python
    rejection_reason: RejectionReason | None = None
```
(c) Add a validator directly after `_pending_reason_iff_pending` (after line 56):
```python
    @model_validator(mode="after")
    def _rejection_reason_only_when_rejected(self) -> "Claim":
        if self.rejection_reason is not None and self.status != Status.REJECTED:
            raise ValueError(
                f"`rejection_reason` is only valid when status=REJECTED; "
                f"got status={self.status.value}"
            )
        return self
```

- [ ] **Step 5: Export `RejectionReason`**

In `grammar/src/polymer_grammar/__init__.py`: change `from .status import PendingReason, Status` (line 15)
to `from .status import PendingReason, RejectionReason, Status`, and add `"RejectionReason",` to `__all__`
(next to the existing `"PendingReason",`).

- [ ] **Step 6: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_rejection_reason.py -q`
Expected: PASS (6 passed).

- [ ] **Step 7: Confirm no regression + lint**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: all existing grammar tests still pass (additive field, default None), ruff clean.

- [ ] **Step 8: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/status.py grammar/src/polymer_grammar/claim.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_rejection_reason.py
git commit -m "feat(grammar): RejectionReason + Claim.rejection_reason + PendingReason.REINSTATED (reinstatement)"
```

---

### Task 2: Protocol — stamp the rejection cause in VERIFY

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py`
- Test: `protocol/tests/test_verify.py`

- [ ] **Step 1: Write the failing tests**

Add to `protocol/tests/test_verify.py` (the file already imports `make_claim`, `make_plan`,
`CycleScaffolding`, `verify_stage`, and defines `_run_to_records`):

```python
def test_out_of_extension_rejection_stamps_defeat_grounded_out(empty_ledger, ctx, adapters):
    from polymer_grammar import RejectionReason
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=())  # a is OUT (satisfied but grounded-out)
    out = verify_stage(corpus, scaffolding, records)
    a = out.by_id()["a"]
    assert a.status == Status.REJECTED
    assert a.rejection_reason == RejectionReason.DEFEAT_GROUNDED_OUT


def test_refuted_rejection_stamps_refuted(empty_ledger, ctx, adapters):
    from polymer_grammar import RejectionReason
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.99, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=("a",))  # IN extension, but refuted
    out = verify_stage(corpus, scaffolding, records)
    a = out.by_id()["a"]
    assert a.status == Status.REJECTED
    assert a.rejection_reason == RejectionReason.REFUTED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd protocol && uv run pytest tests/test_verify.py -q -k "stamps"`
Expected: FAIL (rejection_reason is None — the branch isn't split yet).

- [ ] **Step 3: Split the rejection branch + stamp**

In `protocol/src/polymer_protocol/verify.py`:
(a) Add `RejectionReason` to the existing `from polymer_grammar import (...)` block (the one importing
`Status`, `LicenseRoute`, etc.).
(b) Replace the combined rejection branch (currently `elif agreed_refuted or c.id not in in_ext:` with
its single `_with_status(... pending_reason=None)` append) with two arms — **refutation takes
precedence**:

```python
        elif agreed_refuted:
            new_claims.append(_with_status(
                c, status=Status.REJECTED, licensing=None, pending_reason=None,
                rejection_reason=RejectionReason.REFUTED,
            ))
        elif c.id not in in_ext:
            new_claims.append(_with_status(
                c, status=Status.REJECTED, licensing=None, pending_reason=None,
                rejection_reason=RejectionReason.DEFEAT_GROUNDED_OUT,
            ))
```

(`_with_status` already does `Claim.model_validate(claim.model_copy(update=update).model_dump())`, so the
extra `rejection_reason=` kwarg flows through and re-validates.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd protocol && uv run pytest tests/test_verify.py -q`
Expected: PASS (the two new tests + all existing verify tests — the existing
`test_satisfied_but_outside_extension_is_rejected` / `test_refuted_claim_is_rejected` still pass since
status is unchanged).

- [ ] **Step 5: Lint**

Run: `cd protocol && uv run ruff check src tests`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_verify.py
git commit -m "feat(protocol): VERIFY stamps rejection cause (REFUTED vs DEFEAT_GROUNDED_OUT)"
```

---

### Task 3: Protocol — INTEGRATE stamping + reinstatement block

**Files:**
- Modify: `protocol/src/polymer_protocol/integrate.py`
- Test: `protocol/tests/test_integrate.py`

- [ ] **Step 1: Write the failing tests**

Add to `protocol/tests/test_integrate.py` (the file already imports `make_claim`, `make_plan`,
`DefeatEdge`, `DefeatEdgeKind`, `FDRLedger`, `Status`, `Corpus`, `CycleScaffolding`, `integrate`, and
defines `_licensed_A_with_discovery`). Add `PendingReason` and `RejectionReason` to the
`from polymer_grammar import (...)` block at the top, and add:

```python
def test_defeat_stamps_rejection_reason():
    a, ledger = _licensed_A_with_discovery()
    b = make_claim("B", status=Status.PENDING)
    edge = DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=ledger)
    scaff = CycleScaffolding(grounded_extension=("A", "B"))
    out, _ = integrate(corpus, scaff, ())
    a2 = next(c for c in out.claims if c.id == "A")
    assert a2.status == Status.REJECTED
    assert a2.rejection_reason == RejectionReason.DEFEAT_GROUNDED_OUT


def test_reinstatement_reopens_defeat_rejected_to_pending(empty_ledger):
    # A was defeat-rejected (its attacker B knocked it out). Now C defeats B, so grounded semantics
    # brings A back IN (flipped_in) -> A reopens to PENDING(REINSTATED) to re-test.
    a = make_claim("A", status=Status.REJECTED,
                   rejection_reason=RejectionReason.DEFEAT_GROUNDED_OUT,
                   plan=make_plan(0.01, 0.05))
    b = make_claim("B", status=Status.PENDING)
    c = make_claim("C", status=Status.LICENSED)
    edges = (DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.REBUT),
             DefeatEdge(source="C", target="B", kind=DefeatEdgeKind.REBUT))
    corpus = Corpus(claims=(a, b, c), defeat_edges=edges, fdr_ledger=empty_ledger)
    scaff = CycleScaffolding(grounded_extension=("C", "B"))  # prior: A OUT
    out, _ = integrate(corpus, scaff, ())
    a2 = next(x for x in out.claims if x.id == "A")
    assert a2.status == Status.PENDING
    assert a2.pending_reason == PendingReason.REINSTATED
    assert a2.rejection_reason is None


def test_refuted_claim_in_extension_not_reopened(empty_ledger):
    # A REFUTED claim with no attackers sits in the grounded in_set every cycle (flipped_in) — it must
    # NOT be reopened (refutation is terminal). This is the correctness guard.
    r = make_claim("R", status=Status.REJECTED,
                   rejection_reason=RejectionReason.REFUTED,
                   plan=make_plan(0.01, 0.05))
    corpus = Corpus(claims=(r,), defeat_edges=(), fdr_ledger=empty_ledger)
    scaff = CycleScaffolding(grounded_extension=())  # R out prior; no attackers -> R in in_set
    out, _ = integrate(corpus, scaff, ())
    r2 = next(x for x in out.claims if x.id == "R")
    assert r2.status == Status.REJECTED
    assert r2.rejection_reason == RejectionReason.REFUTED


def test_defeat_rejected_without_plan_not_reopened(empty_ledger):
    # A planless reinstated claim could never self-relicense -> the has-plan gate skips it.
    a = make_claim("A", status=Status.REJECTED,
                   rejection_reason=RejectionReason.DEFEAT_GROUNDED_OUT)  # no plan
    b = make_claim("B", status=Status.PENDING)
    c = make_claim("C", status=Status.LICENSED)
    edges = (DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.REBUT),
             DefeatEdge(source="C", target="B", kind=DefeatEdgeKind.REBUT))
    corpus = Corpus(claims=(a, b, c), defeat_edges=edges, fdr_ledger=empty_ledger)
    scaff = CycleScaffolding(grounded_extension=("C", "B"))
    out, _ = integrate(corpus, scaff, ())
    a2 = next(x for x in out.claims if x.id == "A")
    assert a2.status == Status.REJECTED  # planless -> not reopened
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd protocol && uv run pytest tests/test_integrate.py -q -k "reinstat or stamps or not_reopened"`
Expected: FAIL (`_reject` doesn't stamp the reason yet; no reinstatement block).

- [ ] **Step 3: Stamp `_reject` + add `_reinstate` + the reinstatement block**

In `protocol/src/polymer_protocol/integrate.py`:
(a) Extend the grammar import block to add `PendingReason` and `RejectionReason`:
```python
from polymer_grammar import (
    Claim,
    PendingReason,
    RejectionReason,
    Status,
    derived_rebut_edges,
    restore_consistency,
    retract_tests,
)
```
(b) Stamp the cause in `_reject` (add `rejection_reason` to its update dict):
```python
def _reject(c: Claim) -> Claim:
    """De-license a grounded-OUT survivor: flip to REJECTED + clear licensing + record the cause
    (DEFEAT_GROUNDED_OUT) so a later reinstatement can tell it from a refuted claim."""
    return Claim.model_validate(
        c.model_copy(
            update={
                "status": Status.REJECTED,
                "licensing": None,
                "pending_reason": None,
                "rejection_reason": RejectionReason.DEFEAT_GROUNDED_OUT,
            }
        ).model_dump()
    )
```
(c) Add a `_reinstate` helper directly below `_reject`:
```python
def _reinstate(c: Claim) -> Claim:
    """Reopen a defeat-rejected claim whose attacker has fallen (grounded-IN again) to PENDING so it
    RE-TESTS on current data — never auto-relicense a possibly-stale license. Mirrors drift.reopen_drifted."""
    return Claim.model_validate(
        c.model_copy(
            update={
                "status": Status.PENDING,
                "licensing": None,
                "pending_reason": PendingReason.REINSTATED,
                "rejection_reason": None,
            }
        ).model_dump()
    )
```
(d) In `integrate`, add the reinstatement set beside `defeated_licensed` and apply `_reinstate` in the
comprehension. Replace the block from `defeated_licensed = {...}` through the `new_claims = tuple(...)`
line with:
```python
    defeated_licensed = {
        c.id for c in rr.claims if c.id in rr.flipped_out and c.status == Status.LICENSED
    }
    # Symmetric to the de-license: a defeat-rejected claim that grounded-IN again (its attacker fell)
    # reopens to PENDING to re-test. flipped_out and flipped_in are disjoint, so both apply in one pass.
    reinstated = {
        c.id for c in rr.claims
        if c.id in rr.flipped_in
        and c.status == Status.REJECTED
        and c.rejection_reason == RejectionReason.DEFEAT_GROUNDED_OUT
        and c.evaluation_plan is not None
    }
    removed = rr.retraction.possibly_retracted if rr.retraction is not None else frozenset()
    retract_ids = frozenset(defeated_licensed) | removed
    new_claims = tuple(
        _reject(c) if c.id in defeated_licensed
        else _reinstate(c) if c.id in reinstated
        else c
        for c in rr.claims
    )
```
(Leave the `new_ledger = retract_tests(...)` and `new_corpus = ...` lines unchanged — no new tombstone on
reinstatement; the claim's e-LOND test was already retracted at defeat-rejection.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd protocol && uv run pytest tests/test_integrate.py -q`
Expected: PASS (4 new + all existing integrate tests, including the Phase-2.2 defeat tests which now
also see `rejection_reason=DEFEAT_GROUNDED_OUT` but assert only on status/licensing/ledger).

- [ ] **Step 5: Confirm full protocol suite + lint**

Run: `cd protocol && uv run pytest -q && uv run ruff check src tests`
Expected: all protocol tests pass (the reinstatement block is dormant unless a defeat-rejected claim
flips in — byte-identical for every existing test), ruff clean.

- [ ] **Step 6: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/integrate.py protocol/tests/test_integrate.py
git commit -m "feat(protocol): INTEGRATE reinstatement — reopen defeat-rejected claims to PENDING"
```

---

### Task 4: Full green gate + CONTINUE update

**Files:**
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Run the full gate**

Run: `cd /Users/zbb2/Desktop/polymer-claims && bash scripts/check-all.sh`
Expected: `ALL GREEN`. New counts: grammar +6 (rejection_reason), protocol +6 (2 verify + 4 integrate);
umbrella + isolation unchanged. If anything fails, fix before proceeding.

- [ ] **Step 2: Update CONTINUE.md**

In `docs/superpowers/CONTINUE.md`:
- Add to the **Done — checklist** (under "Phase 2 — epistemic core", below the §2E line):
  `✅ Reinstatement → PENDING — defeat-rejected claims reopen to re-test when their attacker falls (RejectionReason marker + INTEGRATE reinstatement block, symmetric to Phase 2.2).`
- In **▶ NEXT**, mark item 1 (Reinstatement) done and promote n-DMPs-at-FDR and Procrustes (+ the §2E
  follow-ups) as the remaining slices.
- Update the **Current state** test counts to the new totals from Step 1.

- [ ] **Step 3: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add docs/superpowers/CONTINUE.md
git commit -m "docs(reinstatement): reinstatement DONE — CONTINUE checklist + NEXT advance"
```

---

## Self-review notes (for the implementer)

- **Spec coverage:** grammar marker + REINSTATED + validator (Task 1) · VERIFY cause-stamping (Task 2) ·
  INTEGRATE stamping + reinstatement block + has-plan gate + correctness guard (Task 3) · gate + docs
  (Task 4). `ROBUSTLY_BLAMED` is defined-but-unstamped by design (no protocol consumer — noted in spec
  Out-of-scope).
- **Re-test, not auto-relicense:** `_reinstate` clears `licensing` and reopens to PENDING; re-licensing
  happens via the normal VERIFY path in a later cycle (Phase-2.4 live-dedup grants a fresh e-test).
- **No new tombstone:** the reinstated claim's e-LOND test was already retracted at defeat (Phase 2.2);
  a PENDING claim carries no live discovery, so `LICENSED ⇒ live discovery` holds.
- **Back-compat:** `rejection_reason` defaults None; the reinstatement set is empty unless a
  defeat-rejected claim flips in — byte-identical for all existing tests. grammar/protocol pure +
  numpy-free; Corpus = 4.
- **Disjointness:** `flipped_out` (de-license) and `flipped_in` (reinstate) are set-disjoint by
  construction, so the single-pass comprehension never double-acts on a claim.
