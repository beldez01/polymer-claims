# Phase 2.2 — defeat-as-e-value-update + alpha-wealth refund — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a successful defeat de-license a claim AND retract (tombstone) its e-LOND discovery, so de-license flows through the ledger and `LICENSED ⇒ a live e-LOND discovery` becomes an invariant.

**Architecture:** Pure grammar + protocol. Grammar gains `FDRTest.retracted` + live-discovery counts + a pure `retract_tests`. INTEGRATE, after `restore_consistency`, flips grounded-OUT LICENSED survivors to REJECTED and tombstones their discoveries (plus AGM-removed ones). Reuses the proven grounded/Pareto contest as the defeat decision — no per-attack e-value is fabricated.

**Tech Stack:** Python, pydantic v2 (frozen IR models), pytest. Spec: `docs/specs/2026-06-12-phase-2-2-defeat-evalue-refund-design.md`. North Star §2(B).

---

## File Structure

- **Modify** `grammar/src/polymer_grammar/fdr.py` — `FDRTest.retracted: bool = False`; live-discovery counts; add `retract_tests`.
- **Modify** `grammar/src/polymer_grammar/__init__.py` — export `retract_tests`.
- **Modify** `protocol/src/polymer_protocol/integrate.py` — defeat-de-license + refund block + `_reject` helper.
- **Tests** — grammar `test_fdr.py` (retracted counts + `retract_tests` + α-clawback); protocol `test_integrate.py` (de-license + refund + AGM-removed + back-compat).

### Background facts (verified against the code)
- `FDRTest` (post-Phase-2.1): `index, claim_id, e_value (ge=0), alpha_allocated, discovery`. `process_test` sets `alpha = target_fdr·_gamma(t)·(n_discoveries+1)` where `t = n_tests+1`; `discovery = e_value >= 1/alpha`. `_gamma(j) = (6/π²)/j²`.
- `FDRLedger.n_discoveries`/`discoveries`/`is_discovery` currently count `t.discovery` (no retracted notion yet).
- `grammar/__init__.py:60-67` imports from `.fdr`; the `__all__` block lists `"FDRLedger"`, `"FDRTest"`, `"elond_decisions"`, `"is_discovery"`, `"process_stream"`, `"process_test"`.
- `restore_consistency(claims, edges, *, prior_in) -> RevisionResult` (`grammar/revision.py`). `RevisionResult` has `.claims` (consistent_core survivors), `.edges`, `.retraction` (a `RetractionVerdict` with `.possibly_retracted`), `.in_set`, `.flipped_out` (= `prior_in - in_set`), `.flipped_in`.
- `integrate.py` (current): merges `derived_rebut_edges`, runs `restore_consistency(prior_in=frozenset(scaffolding.grounded_extension))`, returns `corpus.model_copy(update={"claims": rr.claims, "defeat_edges": rr.edges}), ()`.
- `effective_defeats`: an attack stands unless the target strength-dominates the source. **An attacker with `strength=None` always defeats** (the dominance guard needs both strengths non-None). So a `strength=None` attacker B with an authored `DefeatEdge(B→A, REBUT)` grounds A OUT.
- `verify.py` flips a grounded-OUT executed claim via `Claim.model_validate(claim.model_copy(update={"status": Status.REJECTED, "licensing": None, "pending_reason": None}).model_dump())` (re-runs validators; a bare `model_copy` skips them).
- `Claim` validator `_licensing_only_when_licensed`: `licensing` is valid only when `status==LICENSED` (so de-licensing MUST set `licensing=None` when flipping away from LICENSED).
- `CycleScaffolding(grounded_extension: tuple[str,...] = (), frontier: tuple[str,...] = ())`.
- conftest helpers: `make_claim(cid, status=..., *, plan=, strength=, **extra)`, `make_plan(value, threshold, comparator=)`. `make_claim` passes `**extra` to `Claim`, so `licensing=` flows through.

---

## Task 1: the tombstone (grammar `fdr.py`)

**Files:**
- Modify: `grammar/src/polymer_grammar/fdr.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_fdr.py`

- [ ] **Step 1: Add the failing tests** (append to `grammar/tests/test_fdr.py`; also add `retract_tests` to its `from polymer_grammar.fdr import (...)` block):

```python
def test_retracted_discovery_not_counted():
    led = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="a", e_value=100.0, alpha_allocated=0.03, discovery=True),
        FDRTest(index=2, claim_id="b", e_value=100.0, alpha_allocated=0.02, discovery=True, retracted=True),
    ))
    assert led.n_discoveries == 1            # b is tombstoned
    assert led.discoveries == frozenset({"a"})
    assert is_discovery(led, "a") is True
    assert is_discovery(led, "b") is False   # retracted -> not a live discovery


def test_retract_tests_marks_matching_claim_ids():
    led = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="a", e_value=100.0, alpha_allocated=0.03, discovery=True),
        FDRTest(index=2, claim_id="b", e_value=100.0, alpha_allocated=0.02, discovery=True),
    ))
    out = retract_tests(led, {"a"})
    assert out.tests[0].retracted is True and out.tests[1].retracted is False
    assert out.n_discoveries == 1
    # immutable: original untouched
    assert led.tests[0].retracted is False
    # no-op for unknown ids returns an equal ledger
    assert retract_tests(led, {"zzz"}).tests == led.tests


def test_process_test_after_retraction_uses_live_discovery_count():
    # two discoveries, retract one -> live D=1. A 3rd test's alpha uses (live_D + 1) = 2, not 3.
    led = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="a", e_value=100.0, alpha_allocated=0.03, discovery=True),
        FDRTest(index=2, claim_id="b", e_value=100.0, alpha_allocated=0.02, discovery=True),
    ))
    led = retract_tests(led, {"a"})          # live discoveries now 1
    led = process_test(led, "c", 100.0)      # t = 3 (n_tests stays 2 -> +1)
    assert led.tests[2].alpha_allocated == pytest.approx(0.05 * _gamma(3) * (1 + 1))
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m pytest grammar/tests/test_fdr.py -q`
Expected: FAIL — `FDRTest` has no `retracted` / cannot import `retract_tests`.

- [ ] **Step 3: Implement in `grammar/src/polymer_grammar/fdr.py`**

(a) Add the field to `FDRTest`:
```python
class FDRTest(_Model):
    index: int
    claim_id: str
    e_value: float = Field(ge=0.0)
    alpha_allocated: float
    discovery: bool
    retracted: bool = False               # defeat tombstone: a retracted discovery is no longer live
```

(b) Make the three count helpers live-only:
```python
    @property
    def n_discoveries(self) -> int:
        return sum(1 for t in self.tests if t.discovery and not t.retracted)

    @property
    def discoveries(self) -> frozenset[str]:
        return frozenset(t.claim_id for t in self.tests if t.discovery and not t.retracted)
```
(`is_discovery(ledger, claim_id)` already reads `ledger.discoveries`, so it excludes retracted automatically — leave it unchanged.)

(c) Add `retract_tests` (after `process_stream`):
```python
def retract_tests(ledger: FDRLedger, claim_ids: Iterable[str]) -> FDRLedger:
    """Tombstone every test whose claim_id is in `claim_ids` (defeat refund): set retracted=True so
    it drops out of the live discovery count. Recorded alpha/e_value are FROZEN (never re-derived).
    Pure/immutable; a no-op (no matching live test) returns an equal-tests ledger."""
    ids = frozenset(claim_ids)
    new_tests = tuple(
        t.model_copy(update={"retracted": True}) if (t.claim_id in ids and not t.retracted) else t
        for t in ledger.tests
    )
    if new_tests == ledger.tests:
        return ledger
    return ledger.model_copy(update={"tests": new_tests})
```

- [ ] **Step 4: Export `retract_tests` in `grammar/src/polymer_grammar/__init__.py`**

Add `retract_tests` to the `from .fdr import (...)` block (line ~60-67) and to the `__all__` list (next to `"process_test"`):
```python
from .fdr import (
    FDRLedger,
    FDRTest,
    elond_decisions,
    is_discovery,
    process_stream,
    process_test,
    retract_tests,
)
```
and in `__all__`: add `"retract_tests",`.

- [ ] **Step 5: Run, confirm PASS**

Run: `python -m pytest grammar/tests/test_fdr.py -q`
Expected: PASS.

- [ ] **Step 6: Grammar suite + ruff**

Run: `python -m pytest grammar/ -q` and `ruff check grammar/src/polymer_grammar/fdr.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_fdr.py`
Expected: PASS / clean. (`retracted` defaults False, so every existing `FDRTest(...)`/ledger test is unaffected.)

- [ ] **Step 7: Commit**

```bash
git add grammar/src/polymer_grammar/fdr.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_fdr.py
git commit -m "feat(grammar): FDRTest.retracted + retract_tests — defeat tombstone, live-discovery counts (Phase 2.2)"
```

---

## Task 2: defeat de-licenses + refunds (protocol `integrate.py`)

**Files:**
- Modify: `protocol/src/polymer_protocol/integrate.py`
- Test: `protocol/tests/test_integrate.py`

- [ ] **Step 1: Write the failing tests** (append to `protocol/tests/test_integrate.py`)

First, a helper to build a LICENSED claim carrying a live discovery (reuse the conftest `make_claim`; look at `protocol/tests/test_drift.py` for an existing LICENSED-with-Licensing construction if the snippet below needs adjustment):
```python
from polymer_grammar import (
    DefeatEdge, DefeatEdgeKind, FDRLedger, FDRTest, LicenseRoute, Licensing,
    MaterializationContext, RivalSetClosure, Satisfaction, SatisfactionVerdict, Status,
)
from polymer_protocol.corpus import Corpus, CycleScaffolding
from polymer_protocol.integrate import integrate
from tests.conftest import make_claim


def _licensing():
    return Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(id="M", api_version="v1", data_version="d1"),
        ),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
    )


def _licensed_A_with_discovery():
    a = make_claim("A", status=Status.LICENSED, licensing=_licensing())
    ledger = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="A", e_value=1e6, alpha_allocated=0.03, discovery=True),
    ))
    return a, ledger


def test_defeat_delicenses_and_refunds_discovery():
    a, ledger = _licensed_A_with_discovery()
    b = make_claim("B", status=Status.PENDING)                      # no strength -> effective defeat
    edge = DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=ledger)
    scaff = CycleScaffolding(grounded_extension=("A", "B"))         # A WAS grounded-IN
    out, _ = integrate(corpus, scaff, ())
    a2 = next(c for c in out.claims if c.id == "A")
    assert a2.status == Status.REJECTED          # de-licensed: grounded-OUT survivor flips
    assert a2.licensing is None
    assert out.fdr_ledger.n_discoveries == 0     # refund: A's discovery tombstoned
    assert out.fdr_ledger.tests[0].retracted is True
    # B (the attacker) is untouched
    assert next(c for c in out.claims if c.id == "B").status == Status.PENDING


def test_no_defeat_is_back_compat():
    a, ledger = _licensed_A_with_discovery()
    corpus = Corpus(claims=(a,), defeat_edges=(), fdr_ledger=ledger)
    scaff = CycleScaffolding(grounded_extension=("A",))
    out, _ = integrate(corpus, scaff, ())
    a2 = next(c for c in out.claims if c.id == "A")
    assert a2.status == Status.LICENSED          # unchanged
    assert out.fdr_ledger.n_discoveries == 1     # ledger unchanged
    assert out.fdr_ledger.tests[0].retracted is False
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m pytest protocol/tests/test_integrate.py -k "defeat or back_compat" -v`
Expected: `test_defeat_delicenses_and_refunds_discovery` FAILS — A stays LICENSED, `n_discoveries` stays 1 (the new behavior isn't implemented). `test_no_defeat_is_back_compat` likely already passes.

- [ ] **Step 3: Implement the de-license + refund in `integrate.py`**

Replace the file body with (imports + the new block):
```python
from __future__ import annotations

from polymer_grammar import (
    Claim,
    Status,
    derived_rebut_edges,
    restore_consistency,
    retract_tests,
)

from .corpus import Corpus, CycleScaffolding, ExecRecord


def _merge_edges(authored, derived):
    seen = {(e.source, e.target, e.kind) for e in authored}
    out = list(authored)
    for e in derived:
        key = (e.source, e.target, e.kind)
        if key not in seen:
            seen.add(key)
            out.append(e)
    return tuple(out)


def _reject(c: Claim) -> Claim:
    """De-license a grounded-OUT survivor: flip to REJECTED + clear licensing (mirrors VERIFY's
    grounded-OUT path; re-validates so the licensing-only-when-LICENSED invariant holds)."""
    return Claim.model_validate(
        c.model_copy(
            update={"status": Status.REJECTED, "licensing": None, "pending_reason": None}
        ).model_dump()
    )


def integrate(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
) -> tuple[Corpus, tuple[str, ...]]:
    # 1. derived rebut edges from the post-VERIFY claims, merged with authored.
    merged = _merge_edges(corpus.defeat_edges, derived_rebut_edges(corpus.claims))
    # 2. entrenchment contest (newcomer yields per AGM).
    rr = restore_consistency(
        corpus.claims, merged, prior_in=frozenset(scaffolding.grounded_extension)
    )
    # 3. defeat = de-license + e-LOND refund (Phase 2.2). A LICENSED survivor grounded-OUT this cycle
    #    flips REJECTED; its discovery (and any AGM-removed claim's discovery) is tombstoned, so the
    #    live FDR count reflects only undefeated discoveries. Defeat and FDR are one mechanism.
    defeated_licensed = {
        c.id for c in rr.claims if c.id in rr.flipped_out and c.status == Status.LICENSED
    }
    removed = rr.retraction.possibly_retracted if rr.retraction is not None else frozenset()
    retract_ids = frozenset(defeated_licensed) | removed
    new_claims = tuple(_reject(c) if c.id in defeated_licensed else c for c in rr.claims)
    new_ledger = retract_tests(corpus.fdr_ledger, retract_ids)

    new_corpus = corpus.model_copy(
        update={"claims": new_claims, "defeat_edges": rr.edges, "fdr_ledger": new_ledger}
    )
    return new_corpus, ()
```

- [ ] **Step 4: Run, confirm PASS**

Run: `python -m pytest protocol/tests/test_integrate.py -k "defeat or back_compat" -v`
Expected: both PASS.

- [ ] **Step 5: Add the AGM-removed refund test**

Append a test that a LICENSED claim REMOVED by an AGM `INCOMPATIBLE_WITH` conflict also has its discovery tombstoned. Build the conflict by mirroring an existing `restore_consistency`/`INCOMPATIBLE_WITH` setup — search `grep -rn "INCOMPATIBLE_WITH\|incompatible" grammar/tests/test_revision.py protocol/tests/test_integrate.py` and reuse that construction (two claims with mutually `incompatible_with` conclusions, the licensed one less entrenched so it is the retracted member). Assert the removed claim is absent from `out.claims` AND `out.fdr_ledger` has its test `retracted` (`n_discoveries` dropped). If building a valid `INCOMPATIBLE_WITH` conclusion pair proves heavy, it is acceptable to assert the refund path directly at the unit level instead: `retract_tests` is already covered in Task 1; the integration point (`removed = rr.retraction.possibly_retracted` feeding `retract_ids`) is exercised — note in your report which form you used.

- [ ] **Step 6: Run the protocol suite (the migration step)**

Run: `python -m pytest protocol/ -q`
Expected: PASS — **but** any existing test that set up a LICENSED claim attacked into a grounded-OUT state and asserted it STAYS LICENSED will now fail (the new correct behavior flips it to REJECTED). For each failure: confirm it is the intended behavior change (a grounded-OUT LICENSED claim SHOULD de-license), then migrate the assertion to expect `REJECTED` + (if it had a discovery) the tombstone. Report every test you migrated and why. Do NOT relax a real regression — only migrate assertions that encode the OLD staleness.

- [ ] **Step 7: ruff + commit**

```bash
ruff check protocol/src/polymer_protocol/integrate.py protocol/tests/test_integrate.py
git add protocol/src/polymer_protocol/integrate.py protocol/tests/test_integrate.py
git commit -m "feat(protocol): defeat de-licenses + refunds the e-LOND discovery (Phase 2.2)"
```

---

## Task 3: full-suite green

**Files:** none (verification + any cross-suite migration).

- [ ] **Step 1: Umbrella + protocol + grammar**

Run: `python -m pytest grammar/ protocol/ tests/ -q`
Expected: PASS. Migrate any remaining test that encoded the old LICENSED-grounded-OUT staleness (search `grep -rln "LICENSED" protocol/tests tests` and check any that build an attacked licensed claim). Report each migration.

- [ ] **Step 2: check-all.sh**

Run: `./scripts/check-all.sh`
Expected: ALL GREEN (grammar fdr + protocol integrate changed; viewer untouched). Fix forward; do not relax assertions.

- [ ] **Step 3: Commit any fixups**

```bash
git add -A
git commit -m "chore(phase2.2): lint/format/test migration fixups"
```
(Skip if nothing changed.)

---

## Self-Review (completed)

**Spec coverage:** §2 tombstone (`FDRTest.retracted` + counts + `retract_tests`) → Task 1; §3 INTEGRATE de-license + refund → Task 2; §6 tests (grammar counts/α-clawback, integrate de-license/refund/AGM-removed/back-compat) → Tasks 1–2; the latent-staleness migration → Task 2 Step 6 + Task 3. All spec sections map to a task.

**Type/name consistency:** `retracted` (bool), `retract_tests(ledger, claim_ids) -> FDRLedger`, `rr.flipped_out`/`rr.retraction.possibly_retracted`, `_reject(c)`, `Status.REJECTED`, `licensing=None` used identically across tasks. The integrate block uses only fields confirmed present on `RevisionResult`.

**Placeholder scan:** none — every code step shows the actual code; the one open construction (AGM-removed conflict, Task 2 Step 5) points to a concrete existing setup to mirror and gives an explicit acceptable fallback.

**Risk flagged:** the latent-staleness fix (grounded-OUT LICENSED → REJECTED) is new behavior; Task 2 Step 6 and Task 3 Step 1 make migrating any test that encoded the old behavior an explicit, reported step (migrate only assertions encoding the staleness, never a real regression).
