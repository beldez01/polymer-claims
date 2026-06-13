# Phase 2.3 — wire the e-LOND gate into the live node — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the running `NodeRunner` license under the 4-way e-LOND gate by threading `evidence_map(self.corpus)` into the live `run_cycle`, behind an opt-in `evalue_gate` flag.

**Architecture:** Umbrella-only (`node.py`); grammar/protocol untouched; Corpus stays 4. Opt-in, byte-identical default. `evidence_map` is **lazily imported inside `tick`** to keep `node.py`'s base import numpy-free (`evidence.py` imports numpy; `materialization_map` doesn't). Near-exact parallel to CES-4's `materialization_map` wiring.

**Tech Stack:** Python, pydantic v2, pytest. Spec: `docs/specs/2026-06-13-phase-2-3-live-egate-design.md`.

---

## Background facts (verified)
- `NodeRunner.__init__`/`from_seed` already carry `content_address: bool = False` + `profiles` (CES-4); `tick`'s `RUN_CYCLE` branch (`node.py:156-169`) computes `mats = materialization_map(...) if self.content_address else None` and calls `run_cycle(..., materializations=mats, **self.run_cycle_kwargs)`.
- `run_cycle` accepts a keyword `evidence: dict[str,float] | None = None` (Phase 2.1).
- `evidence_map(corpus) -> dict[str,float]` (`src/polymer_claims/evidence.py`) imports numpy at module top; `import polymer_claims.node` does NOT pull numpy today (must stay true).
- `tests/conftest.py` `methyl_node(**kwargs)` builds a one-claim methyl corpus with `region_delta_beta_claim("c-true", threshold=0.10)` (the NOISELESS demo fixture), pops `content_address`, passes remaining `**kwargs` to `NodeRunner`.
- The well-powered fixture `epicv2_casectrl_powered@1` has a STRONG region `cg00000001-05` (Δβ≈0.30, e≈1703 > bar 32.9) and a WEAK region `cg00000006-10` (Δβ≈0.12 > 0.10 SATISFIED, e≈2.28 < bar).
- `region_delta_beta_claim(claim_id, *, ref, region_probes, threshold, ...)`.

---

## Task 1: the flag + live wiring + tests

**Files:**
- Modify: `src/polymer_claims/node.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_node_evalue_gate.py`

- [ ] **Step 1: Let `methyl_node` accept a `claim` override**

In `tests/conftest.py` `methyl_node`, replace the fixed claim line with a `claim` pop (so a test can supply a powered-fixture claim), keeping the default:
```python
    claim = kwargs.pop("claim", None) or region_delta_beta_claim("c-true", threshold=0.10)
```
(`kwargs.pop("claim", ...)` must run BEFORE `**kwargs` is forwarded to `NodeRunner`, so `NodeRunner` never receives a `claim` kwarg.)

- [ ] **Step 2: Write the failing tests** at `tests/test_node_evalue_gate.py`:
```python
from __future__ import annotations

import subprocess
import sys

from polymer_grammar import Status

from polymer_claims.methyl_adapters import region_delta_beta_claim
from tests.conftest import methyl_node

_POWERED = "se:epicv2_casectrl_powered@1"
_STRONG = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_WEAK = ("cg00000006", "cg00000007", "cg00000008", "cg00000009", "cg00000010")


def _node(region_probes, **kw):
    claim = region_delta_beta_claim("c-x", ref=_POWERED, region_probes=region_probes, threshold=0.10)
    r = methyl_node(claim=claim, **kw)
    for _ in range(3):
        r.tick()
    return r


def test_egate_licenses_strong_region_live():
    r = _node(_STRONG, evalue_gate=True)
    c = next(x for x in r.corpus.claims if x.id == "c-x")
    assert c.status == Status.LICENSED              # e-gate fired AND passed in the live runner
    assert r.corpus.fdr_ledger.n_discoveries == 1


def test_egate_blocks_weak_region_live():
    r = _node(_WEAK, evalue_gate=True)
    c = next(x for x in r.corpus.claims if x.id == "c-x")
    assert c.status != Status.LICENSED              # point-significant but e below bar -> withheld live
    assert r.corpus.fdr_ledger.n_discoveries == 0


def test_weak_region_licenses_without_egate():
    r = _node(_WEAK, evalue_gate=False)
    c = next(x for x in r.corpus.claims if x.id == "c-x")
    assert c.status == Status.LICENSED              # 3-way gate licenses it: the e-gate is the only difference


def test_node_import_stays_numpy_free():
    code = ("import polymer_claims.node, sys; "
            "assert 'numpy' not in sys.modules, sorted(m for m in sys.modules if 'numpy' in m)")
    subprocess.run([sys.executable, "-c", code], check=True)
```

- [ ] **Step 3: Run, confirm FAIL**

Run: `python -m pytest tests/test_node_evalue_gate.py -q`
Expected: FAIL — `NodeRunner.__init__() got an unexpected keyword argument 'evalue_gate'`.

- [ ] **Step 4: Add `evalue_gate` to `NodeRunner` + wire `tick`**

In `src/polymer_claims/node.py`:

(a) Add `evalue_gate: bool = False` to BOTH `__init__` and `from_seed` (right after `content_address`/`profiles`), store `self.evalue_gate = evalue_gate` in `__init__`, and forward it in `from_seed`'s `cls(...)` call.

(b) In `tick`'s `RUN_CYCLE` branch, after the `mats = ...` block and before `run_cycle(...)`:
```python
            if self.evalue_gate:
                from .evidence import evidence_map   # lazy: keeps node.py base import numpy-free
                ev = evidence_map(self.corpus)
            else:
                ev = None
            result = run_cycle(
                self.corpus,
                self.adapters,
                self.ctx,
                ledger=self.ledger,
                materializations=mats,
                evidence=ev,
                **self.run_cycle_kwargs,
            )
```

- [ ] **Step 5: Run, confirm PASS**

Run: `python -m pytest tests/test_node_evalue_gate.py -q`
Expected: PASS (all four). If `test_egate_licenses_strong_region_live` fails (not LICENSED), print `evidence_map(r.corpus)` after a tick and confirm the strong e-value clears the bar — the powered fixture pins e≈1703, so a failure means the wiring isn't threading `evidence`. If `test_egate_blocks_weak_region_live` shows LICENSED, the weak e exceeded the bar — do NOT relax; recheck the fixture/region.

- [ ] **Step 6: Back-compat — existing node suites**

Run: `python -m pytest tests/test_node.py tests/test_node_content_address.py -q`
Expected: PASS (unchanged — `evalue_gate` defaults False → `evidence=None`).

- [ ] **Step 7: ruff + commit**

```bash
ruff check src/polymer_claims/node.py tests/conftest.py tests/test_node_evalue_gate.py
git add src/polymer_claims/node.py tests/conftest.py tests/test_node_evalue_gate.py
git commit -m "feat(node): evalue_gate — live 4-way e-LOND licensing in NodeRunner.tick (Phase 2.3)"
```

---

## Task 2: full-suite green

**Files:** none (verification).

- [ ] **Step 1:** `python -m pytest tests/ -q` → PASS.
- [ ] **Step 2:** `./scripts/check-all.sh` → ALL GREEN.
- [ ] **Step 3:** Commit any fixups (`git add -A && git commit -m "chore(phase2.3): fixups"`; skip if none).

---

## Self-Review (completed)

**Spec coverage:** §2 flag → Task 1 Step 4a; §3 lazy-import wiring → Step 4b; §6 tests (strong licenses, weak blocked, weak licenses without gate, numpy-free, back-compat) → Steps 2/6. All map.

**Type/name consistency:** `evalue_gate` (bool), `evidence=ev`, lazy `from .evidence import evidence_map`, `methyl_node(claim=...)` used identically.

**Risk:** the numpy-free guarantee rests on the lazy import (Step 4b) — Step 2's subprocess test pins it. The licensing test depends on the powered fixture being present (merged in Phase 2.1) — it is on `main`.
