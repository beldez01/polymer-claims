# Adapter Trust Registry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Make license-grade verification mean genuine adapter independence (different owner / implementation lineage / both trusted), enforced by an operator-curated registry consulted in `verify_stage` — mirroring the `OracleRegistry` precedent. Audit finding #5.

**Spec:** `docs/superpowers/specs/2026-06-05-adapter-trust-registry-design.md` (binding). Decisions: hold-PENDING on non-independence (new `PendingReason.ADAPTER_NOT_INDEPENDENT`); protocol-side audit (no grammar Satisfaction change); opt-in tightening (no/empty registry ⇒ behavior byte-unchanged).

**Architecture:** grammar gains ONE additive enum value; protocol gains an `adapter_registry.py` module (twin of `oracle.py`) + a gate in `verify_stage` + `run_cycle` wiring. Registry passed-in, never persisted (Corpus stays 4). Pure/deterministic; isolation holds.

**Verify (each task):** grammar `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q && uv run ruff check src tests`; protocol `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q && uv run ruff check src tests`; isolation `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_isolation.py -q`; umbrella unaffected `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q`. ABSOLUTE paths.

**Branch:** `feat/adapter-trust-registry` (single branch, 3 sequential tasks).

---

## Task 1: grammar — `PendingReason.ADAPTER_NOT_INDEPENDENT`

**Files:** `grammar/src/polymer_grammar/status.py`; Test `grammar/tests/test_status.py` (or wherever PendingReason is tested — grep for `MATERIALIZATION_DRIFTED`).

- [ ] **Step 1 — failing test:**
```python
def test_adapter_not_independent_reason_exists_and_round_trips():
    from polymer_grammar import PendingReason
    assert PendingReason.ADAPTER_NOT_INDEPENDENT.value == "adapter_not_independent"
    # a PENDING claim may carry it (use the existing claim builder in this test module / conftest)
    c = make_pending_claim(pending_reason=PendingReason.ADAPTER_NOT_INDEPENDENT)
    assert Claim.model_validate_json(c.model_dump_json()).pending_reason is PendingReason.ADAPTER_NOT_INDEPENDENT
```
(Use the existing PendingReason test pattern — find how `MATERIALIZATION_DRIFTED` is tested and mirror it. If there's an exhaustiveness/`len(PendingReason)` assertion anywhere, update its expected count.)
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement:** add `ADAPTER_NOT_INDEPENDENT = "adapter_not_independent"` to the `PendingReason` enum in `status.py` (place it next to `MATERIALIZATION_DRIFTED`, with a short comment: "verify withheld a license: the agreeing adapters are not registry-independent"). Confirm `PendingReason` is exported from `polymer_grammar` (it already is).
- [ ] **Step 4 — green:** grammar full suite + ruff + isolation.
- [ ] **Step 5 — commit** `feat(grammar): PendingReason.ADAPTER_NOT_INDEPENDENT`.

---

## Task 2: protocol — `adapter_registry.py` + exports

**Files:** Create `protocol/src/polymer_protocol/adapter_registry.py`; modify `protocol/src/polymer_protocol/__init__.py`; Test `protocol/tests/test_adapter_registry.py`.

- [ ] **Step 1 — failing test** `protocol/tests/test_adapter_registry.py`:
```python
from polymer_protocol import (
    AdapterCredential, AdapterRegistry, adapters_independent, pair_is_registry_independent,
)

def _cred(identity, owner, h, trusted=True):
    return AdapterCredential(identity=identity, owner=owner, implementation_hash=h, trusted=trusted)

def test_independent_truth_table():
    a = _cred("x", "alice", "h1"); b = _cred("y", "bob", "h2")
    assert adapters_independent(a, b)
    assert not adapters_independent(a, _cred("z", "alice", "h2"))   # same owner
    assert not adapters_independent(a, _cred("z", "bob", "h1"))     # same lineage
    assert not adapters_independent(a, _cred("z", "bob", "h2", trusted=False))  # untrusted

def test_resolve_and_is_empty():
    r = AdapterRegistry()
    assert r.is_empty and r.resolve("x") is None
    r2 = AdapterRegistry(credentials=(_cred("x", "alice", "h1"),))
    assert not r2.is_empty and r2.resolve("x").owner == "alice" and r2.resolve("nope") is None

def test_pair_is_registry_independent():
    r = AdapterRegistry(credentials=(_cred("identity", "alice", "h1"), _cred("reference", "bob", "h2")))
    assert pair_is_registry_independent(r, ("identity", "reference"))
    # an unregistered identity contributes no independent pair
    assert not pair_is_registry_independent(r, ("identity", "ghost"))
    # same-owner registry → no independent pair
    r2 = AdapterRegistry(credentials=(_cred("identity", "alice", "h1"), _cred("reference", "alice", "h2")))
    assert not pair_is_registry_independent(r2, ("identity", "reference"))
```
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement** `adapter_registry.py` per spec: frozen `_Model` subclasses `AdapterCredential` (identity/owner/implementation_hash/version="v1"/trusted=True) and `AdapterRegistry` (credentials tuple; `resolve` linear scan returning the first match or None; `is_empty` property `not self.credentials`); pure `adapters_independent(a, b)` = `a.trusted and b.trusted and a.owner != b.owner and a.implementation_hash != b.implementation_hash`; pure `pair_is_registry_independent(registry, identities)` = any independent resolved pair among `identities` (nested loop, both must resolve non-None). Module docstring: mirror `oracle.py`'s "passed into run_cycle, NEVER persisted" note. Add the four names to `__init__.py` imports + `__all__`.
- [ ] **Step 4 — green:** protocol full suite + ruff + isolation.
- [ ] **Step 5 — commit** `feat(protocol): adapter trust registry + independence predicate`.

---

## Task 3: protocol — the `verify_stage` gate + `run_cycle` wiring + audit + end-to-end

**Files:** `protocol/src/polymer_protocol/verify.py`, `protocol/src/polymer_protocol/cycle.py`; Test `protocol/tests/test_verify.py` (or the existing verify/cycle test module — grep for `verify_stage(` and `run_cycle(`).

- [ ] **Step 1 — failing tests** (through `run_cycle`, using the two reference adapters `IdentityAdapter()` [identity="identity"] + `ReferenceAdapter(identity="reference")` and a corpus whose claim licenses on one cycle — reuse the existing licensing fixture/builder in the protocol test suite):
```python
from polymer_grammar import PendingReason, Status
from polymer_protocol import AdapterCredential, AdapterRegistry, run_cycle

def _registry(owner_a="alice", owner_b="bob", h_a="h1", h_b="h2", trusted_b=True):
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="identity", owner=owner_a, implementation_hash=h_a),
        AdapterCredential(identity="reference", owner=owner_b, implementation_hash=h_b, trusted=trusted_b),
    ))

def test_no_registry_licenses_as_before():   # back-compat
    res = run_cycle(licensing_corpus(), REF_ADAPTERS, CTX)             # no adapter_registry
    assert any(c.status == Status.LICENSED for c in res.corpus.claims)

def test_independent_registry_licenses():
    res = run_cycle(licensing_corpus(), REF_ADAPTERS, CTX, adapter_registry=_registry())
    assert any(c.status == Status.LICENSED for c in res.corpus.claims)

def test_same_owner_holds_pending():
    res = run_cycle(licensing_corpus(), REF_ADAPTERS, CTX, adapter_registry=_registry(owner_b="alice"))
    held = [c for c in res.corpus.claims if c.pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT]
    assert held and all(c.status == Status.PENDING for c in held)
    assert not any(c.status == Status.LICENSED for c in res.corpus.claims)

def test_same_lineage_holds_pending():
    res = run_cycle(licensing_corpus(), REF_ADAPTERS, CTX, adapter_registry=_registry(h_b="h1"))
    assert any(c.pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT for c in res.corpus.claims)
    assert not any(c.status == Status.LICENSED for c in res.corpus.claims)

def test_untrusted_holds_pending():
    res = run_cycle(licensing_corpus(), REF_ADAPTERS, CTX, adapter_registry=_registry(trusted_b=False))
    assert any(c.pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT for c in res.corpus.claims)

def test_unregistered_adapter_holds_pending():
    # registry that registers only one of the two producing identities
    reg = AdapterRegistry(credentials=(AdapterCredential(identity="identity", owner="alice", implementation_hash="h1"),))
    res = run_cycle(licensing_corpus(), REF_ADAPTERS, CTX, adapter_registry=reg)
    assert any(c.pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT for c in res.corpus.claims)

def test_audit_note_reports_held_count():
    res = run_cycle(licensing_corpus(), REF_ADAPTERS, CTX, adapter_registry=_registry(owner_b="alice"))
    vnote = next(a.note for a in res.audit if a.stage == "verify_stage")
    assert "held" in vnote

def test_gate_is_deterministic():
    reg = _registry(owner_b="alice")
    a = run_cycle(licensing_corpus(), REF_ADAPTERS, CTX, adapter_registry=reg)
    b = run_cycle(licensing_corpus(), REF_ADAPTERS, CTX, adapter_registry=reg)
    assert a.model_dump_json() == b.model_dump_json()
```
(Find the exact names of the existing reference-adapters tuple + ctx + licensing corpus builder in the protocol test suite and reuse them; the placeholders `REF_ADAPTERS`/`CTX`/`licensing_corpus()` stand in for whatever that module already uses.)
- [ ] **Step 2 — confirm fail** (unexpected `adapter_registry` kwarg).
- [ ] **Step 3 — implement:**
  - `verify.py`: import `PendingReason`, `Status` (Status already imported) from `polymer_grammar`; import `AdapterRegistry`, `pair_is_registry_independent` from `.adapter_registry`. Add `adapter_registry: AdapterRegistry | None = None` param to `verify_stage`. Inside the LICENSED block, as the FIRST statement (before building `licensing`):
    ```python
    if adapter_registry is not None and not adapter_registry.is_empty:
        identities = tuple(r.adapter_identity for r in ev.results)
        if not pair_is_registry_independent(adapter_registry, identities):
            new_claims.append(_with_status(
                c, status=Status.PENDING,
                pending_reason=PendingReason.ADAPTER_NOT_INDEPENDENT,
                licensing=None,
            ))
            continue
    ```
  - `cycle.py`: add `adapter_registry: AdapterRegistry | None = None` to `run_cycle`'s signature (next to `oracles`); pass it into the `verify_stage(corpus, scaffolding, records, oracles)` call as `verify_stage(corpus, scaffolding, records, oracles, adapter_registry=adapter_registry)`. After verify_stage, compute `n_trust_held = sum(1 for c in corpus.claims if c.pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT)` and enrich the verify StageAudit note → `note=f"{n_licensed} licensed" + (f", {n_trust_held} held (adapter not independent)" if n_trust_held else "")`. Import `PendingReason` in cycle.py if not already.
  - Keep `run_cycle`'s back-compat: default None ⇒ untouched.
- [ ] **Step 4 — green:** protocol full suite (ALL existing tests pass — back-compat) + ruff + isolation BOTH ways + umbrella suite (`run_cycle`/CLI callers unaffected) `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q`.
- [ ] **Step 5 — commit** `feat(protocol): enforce adapter independence at the verify_stage license seam`.

**After 1–3 reviewed:** finish the branch (merge local no-ff, no push); update `docs/superpowers/CONTINUE.md` + the knowledge-protocol memory (note: audit #5 DONE; the heavier Satisfaction-field provenance + real impl-hashing + strict-mode remain deferred).

## Self-Review
- Spec coverage: PendingReason (T1), registry+predicates (T2), gate+wiring+audit+e2e (T3). ✓
- Invariants: 1 additive grammar enum; registry passed-in/not-persisted (Corpus 4); frozen Satisfaction/Licensing untouched; back-compat opt-in (None/empty ⇒ unchanged); pure/deterministic; isolation both ways. ✓
- No placeholders: every file, the exact gate code, the audit-note formula, and the truth-table tests are concrete. `REF_ADAPTERS`/`CTX`/`licensing_corpus` are explicitly flagged to bind to the protocol suite's existing fixtures. ✓
