# H¹ → Duhem Blame-Set Coupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert sheaf H¹ frustration obstructions (global inconsistencies with no local witness) into Duhem–Quine blame verdicts, routing a single frustrated cycle to `PENDING duhem_underdetermined` and a claim shared across multiple cycles to `REJECTED / ROBUSTLY_BLAMED`.

**Architecture:** A new pure module `protocol/src/polymer_protocol/blame_bridge.py` bridges the two mechanisms that already exist but are uncoupled: `Obstruction` (from `polymer_protocol.sheaf`) and the blame-set algebra (`polymer_grammar.blame`). A single obstruction becomes a `BlameSet` of one singleton assignment per cycle member — so its `aggregate_blame` intersection is empty and every member is underdetermined. A separate cross-obstruction function intersects member sets across ≥2 obstructions to find a robustly-blamed common culprit. The reserved `RejectionReason.ROBUSTLY_BLAMED` status is wired via a new non-breaking grammar accessor `duhem_rejection_reason`.

**Tech Stack:** Python 3, pydantic (frozen `_Model`), pytest. No numpy — the bridge stays in the pure protocol layer; only `sheaf_spectrum.py` (the numpy detector, already tested) sits in the umbrella.

## Global Constraints

- **Purity:** `polymer_grammar` and `polymer_protocol` are pure — pydantic + stdlib only, **no numpy**. The bridge module must not import numpy or anything from `polymer_claims` (the umbrella). Verbatim from `blame.py`: "the protocol SUPPLIES the candidate minimal blame-assignments; the grammar only does the tractable set algebra."
- **Determinism:** any ordering derived from claim ids uses `sorted(...)`, matching `_frustration_obstructions` ("Deterministic: sorted ids").
- **Frozen models:** `Obstruction`, `BlameSet`, `BlameAssignment`, `BlameVerdict` are frozen `_Model` (pydantic). Build new instances; never mutate.
- **Non-breaking:** `duhem_status` has an existing test asserting `(Status.REJECTED, None)`. Do NOT change its signature or return; add a sibling accessor for the `RejectionReason`.
- **Single-cycle invariant:** one frustrated cycle has **no local witness** → its members are all `underdetermined`, never `robustly_blamed`. Robust blame requires a claim present in **every** obstruction across ≥2 obstructions.

---

## File structure

| File | Responsibility | Create/Modify |
|---|---|---|
| `grammar/src/polymer_grammar/blame.py` | add `duhem_rejection_reason` accessor | Modify |
| `grammar/src/polymer_grammar/__init__.py` | export `duhem_rejection_reason` | Modify |
| `grammar/tests/test_blame.py` | test the new accessor | Modify |
| `protocol/src/polymer_protocol/blame_bridge.py` | Obstruction → BlameSet / BlameVerdict / statuses | Create |
| `protocol/src/polymer_protocol/__init__.py` | export the three bridge functions | Modify |
| `protocol/tests/test_blame_bridge.py` | unit-test the bridge with hand-built Obstructions | Create |
| `tests/test_sheaf_blame_e2e.py` | umbrella end-to-end: real SheafStructure → obstructions → statuses | Create |

Reference types (already defined, do not create):
- `polymer_protocol.sheaf.Obstruction(_Model)` — `claim_ids: tuple[str, ...]`, `edges: tuple[tuple[str, str], ...]`, `magnitude: float`.
- `polymer_grammar.blame.BlameSet(_Model)` — `contradiction_id: str`, `assignments: tuple[BlameAssignment, ...]` (min_length=1).
- `polymer_grammar.blame.BlameAssignment(_Model)` — `targets: tuple[str, ...]` (min_length=1), `note: str | None`.
- `polymer_grammar.blame.BlameVerdict(_Model)` — `robustly_blamed`, `possibly_blamed`, `underdetermined`: `frozenset[str]`.
- `polymer_grammar.blame.aggregate_blame(BlameSet) -> BlameVerdict`.
- `polymer_grammar.blame.duhem_status(claim_id, verdict) -> tuple[Status, PendingReason | None] | None`.
- `polymer_grammar.status.RejectionReason.ROBUSTLY_BLAMED`.

---

### Task 1: Wire the reserved `ROBUSTLY_BLAMED` status (grammar accessor)

**Files:**
- Modify: `grammar/src/polymer_grammar/blame.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_blame.py`

**Interfaces:**
- Consumes: `BlameVerdict` (existing), `RejectionReason` (existing, in `.status`).
- Produces: `duhem_rejection_reason(claim_id: str, verdict: BlameVerdict) -> RejectionReason | None` — returns `RejectionReason.ROBUSTLY_BLAMED` iff `claim_id in verdict.robustly_blamed`, else `None`.

- [ ] **Step 1: Write the failing test**

Add to `grammar/tests/test_blame.py`:

```python
def test_duhem_rejection_reason_flags_robustly_blamed():
    from polymer_grammar.blame import duhem_rejection_reason
    from polymer_grammar.status import RejectionReason
    v = BlameVerdict(
        robustly_blamed=frozenset({"c1"}),
        possibly_blamed=frozenset({"c1", "c2"}),
        underdetermined=frozenset({"c2"}),
    )
    assert duhem_rejection_reason("c1", v) == RejectionReason.ROBUSTLY_BLAMED
    assert duhem_rejection_reason("c2", v) is None   # underdetermined -> not a rejection
    assert duhem_rejection_reason("c3", v) is None   # not implicated
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && python -m pytest tests/test_blame.py::test_duhem_rejection_reason_flags_robustly_blamed -v`
Expected: FAIL with `ImportError: cannot import name 'duhem_rejection_reason'`.

- [ ] **Step 3: Add the accessor**

In `grammar/src/polymer_grammar/blame.py`, change the import line and append the function:

```python
from .status import PendingReason, RejectionReason, Status
```

```python
def duhem_rejection_reason(claim_id: str, verdict: BlameVerdict) -> RejectionReason | None:
    """The RejectionReason to record when `duhem_status` returns REJECTED for `claim_id`.
    Robust Duhem blame is terminal; this wires the reserved RejectionReason.ROBUSTLY_BLAMED.
    Returns None if the claim is not robustly blamed (PENDING or uninvolved carry no reason)."""
    if claim_id in verdict.robustly_blamed:
        return RejectionReason.ROBUSTLY_BLAMED
    return None
```

- [ ] **Step 4: Export it**

In `grammar/src/polymer_grammar/__init__.py`, add `duhem_rejection_reason` to both the `from .blame import (...)` block and the `__all__` list, alongside the existing `aggregate_blame`:

```python
from .blame import (
    BlameAssignment,
    BlameSet,
    BlameVerdict,
    aggregate_blame,
    duhem_rejection_reason,
)
```
and in `__all__`:
```python
    "aggregate_blame",
    "duhem_rejection_reason",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd grammar && python -m pytest tests/test_blame.py -v`
Expected: PASS (all existing tests + the new one).

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/blame.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_blame.py
git commit -m "feat(blame): wire reserved ROBUSTLY_BLAMED via duhem_rejection_reason accessor"
```

---

### Task 2: `blame_set_from_obstruction` — single cycle → BlameSet (no local witness)

**Files:**
- Create: `protocol/src/polymer_protocol/blame_bridge.py`
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_blame_bridge.py`

**Interfaces:**
- Consumes: `Obstruction` (from `.sheaf`), `BlameSet`, `BlameAssignment`, `aggregate_blame` (from grammar).
- Produces: `blame_set_from_obstruction(obs: Obstruction) -> BlameSet` — one **singleton** `BlameAssignment(targets=(cid,))` per member of `obs.claim_ids`, so `aggregate_blame` yields an empty intersection (no member blamed in every candidate repair) and every member is `underdetermined`. `contradiction_id = "h1:" + "|".join(sorted(obs.claim_ids))` (deterministic).

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_blame_bridge.py`:

```python
from polymer_grammar.blame import aggregate_blame
from polymer_grammar.status import PendingReason, Status
from polymer_protocol.sheaf import Obstruction
from polymer_protocol.blame_bridge import blame_set_from_obstruction


def _cycle(*ids):
    edges = tuple((ids[i], ids[(i + 1) % len(ids)]) for i in range(len(ids)))
    return Obstruction(claim_ids=tuple(ids), edges=edges, magnitude=1.0)


def test_single_cycle_has_no_local_witness_all_underdetermined():
    # the drift 1->1->1->2 loop of epistemology.md §6: A≈B≈C≈A, every edge fine, cycle open
    bs = blame_set_from_obstruction(_cycle("A", "B", "C"))
    assert bs.contradiction_id == "h1:A|B|C"
    v = aggregate_blame(bs)
    assert v.possibly_blamed == frozenset({"A", "B", "C"})
    assert v.robustly_blamed == frozenset()                     # no local witness
    assert v.underdetermined == frozenset({"A", "B", "C"})      # all PENDING duhem
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && python -m pytest tests/test_blame_bridge.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_protocol.blame_bridge'`.

- [ ] **Step 3: Create the module with the function**

Create `protocol/src/polymer_protocol/blame_bridge.py`:

```python
"""Bridge H¹ frustration obstructions to Duhem–Quine blame verdicts.

A frustrated cycle (sheaf H¹, epistemology.md §6) is a contradiction with NO local witness:
every edge looks locally consistent but the cycle does not close. Duhem–Quine: blame can fall
on any member of the bundle, and nothing isolates the culprit. So a single cycle maps to one
singleton candidate-repair per member -> aggregate_blame's intersection is empty -> every member
is `underdetermined` -> PENDING duhem_underdetermined. A claim present in EVERY obstruction across
>=2 obstructions is the robustly-blamed common cause -> REJECTED / ROBUSTLY_BLAMED.

Pure: pydantic + stdlib only; no numpy, no polymer_claims. The numpy detector that produces the
Obstructions lives in the umbrella (`polymer_claims.sheaf_spectrum`); this module never runs it.
"""
from __future__ import annotations

from collections.abc import Sequence

from polymer_grammar.blame import BlameAssignment, BlameSet, BlameVerdict
from polymer_grammar.status import PendingReason, RejectionReason, Status

from .sheaf import Obstruction


def blame_set_from_obstruction(obs: Obstruction) -> BlameSet:
    """One singleton candidate-repair per cycle member: no local witness, so no member is
    blamed in every repair -> aggregate_blame leaves them all underdetermined."""
    members = sorted(obs.claim_ids)
    return BlameSet(
        contradiction_id="h1:" + "|".join(members),
        assignments=tuple(BlameAssignment(targets=(cid,)) for cid in members),
    )
```

- [ ] **Step 4: Export it**

In `protocol/src/polymer_protocol/__init__.py`, after the `from .sheaf import (...)` block add:

```python
from .blame_bridge import (
    blame_set_from_obstruction,
)
```
and add `"blame_set_from_obstruction"` to `__all__` near the sheaf exports.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd protocol && python -m pytest tests/test_blame_bridge.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/blame_bridge.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_blame_bridge.py
git commit -m "feat(blame-bridge): single obstruction -> BlameSet (no-local-witness -> all underdetermined)"
```

---

### Task 3: `blame_verdict_from_obstructions` — the cross-cycle robust-blame path

**Files:**
- Modify: `protocol/src/polymer_protocol/blame_bridge.py`
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_blame_bridge.py`

**Interfaces:**
- Consumes: `Obstruction`, `BlameVerdict`.
- Produces: `blame_verdict_from_obstructions(obstructions: Sequence[Obstruction]) -> BlameVerdict`.
  - `possibly_blamed` = union of all members across all obstructions.
  - `robustly_blamed` = intersection of member sets **only when `len(obstructions) >= 2`**; empty for 0 or 1 obstruction (single cycle has no local witness — the invariant from Global Constraints).
  - `underdetermined` = `possibly_blamed - robustly_blamed`.

- [ ] **Step 1: Write the failing tests**

Append to `protocol/tests/test_blame_bridge.py`:

```python
from polymer_protocol.blame_bridge import blame_verdict_from_obstructions


def test_one_obstruction_is_all_underdetermined_never_robust():
    v = blame_verdict_from_obstructions([_cycle("A", "B", "C")])
    assert v.robustly_blamed == frozenset()
    assert v.underdetermined == frozenset({"A", "B", "C"})


def test_shared_claim_across_two_cycles_is_robustly_blamed():
    # X sits in both frustrated cycles -> the common culprit; the others stay underdetermined
    v = blame_verdict_from_obstructions([_cycle("A", "B", "X"), _cycle("C", "D", "X")])
    assert v.robustly_blamed == frozenset({"X"})
    assert v.possibly_blamed == frozenset({"A", "B", "C", "D", "X"})
    assert v.underdetermined == frozenset({"A", "B", "C", "D"})


def test_no_obstructions_is_empty_verdict():
    v = blame_verdict_from_obstructions([])
    assert v.possibly_blamed == frozenset()
    assert v.robustly_blamed == frozenset()
    assert v.underdetermined == frozenset()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd protocol && python -m pytest tests/test_blame_bridge.py -k obstruction -v`
Expected: FAIL with `ImportError: cannot import name 'blame_verdict_from_obstructions'`.

- [ ] **Step 3: Add the function**

Append to `protocol/src/polymer_protocol/blame_bridge.py`:

```python
def blame_verdict_from_obstructions(obstructions: Sequence[Obstruction]) -> BlameVerdict:
    """Aggregate blame across frustrated cycles. A claim in EVERY obstruction (>=2 of them) is the
    robustly-blamed common culprit; a single cycle has no local witness so nothing is robust."""
    member_sets = [frozenset(o.claim_ids) for o in obstructions]
    if not member_sets:
        empty: frozenset[str] = frozenset()
        return BlameVerdict(robustly_blamed=empty, possibly_blamed=empty, underdetermined=empty)
    union = frozenset().union(*member_sets)
    robust = frozenset.intersection(*member_sets) if len(member_sets) >= 2 else frozenset()
    return BlameVerdict(
        robustly_blamed=robust,
        possibly_blamed=union,
        underdetermined=union - robust,
    )
```

- [ ] **Step 4: Export it**

In `protocol/src/polymer_protocol/__init__.py`, add `blame_verdict_from_obstructions` to the `from .blame_bridge import (...)` block and to `__all__`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd protocol && python -m pytest tests/test_blame_bridge.py -v`
Expected: PASS (all four bridge tests).

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/blame_bridge.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_blame_bridge.py
git commit -m "feat(blame-bridge): cross-cycle robust-blame (shared claim across >=2 obstructions)"
```

---

### Task 4: `duhem_statuses_from_obstructions` — the demonstrable coupling

**Files:**
- Modify: `protocol/src/polymer_protocol/blame_bridge.py`
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_blame_bridge.py`

**Interfaces:**
- Consumes: `blame_verdict_from_obstructions` (Task 3), `duhem_status` + `duhem_rejection_reason` (grammar).
- Produces: `duhem_statuses_from_obstructions(obstructions: Sequence[Obstruction]) -> dict[str, tuple[Status, PendingReason | None, RejectionReason | None]]` — the per-claim verdict every implicated claim should receive: underdetermined → `(PENDING, DUHEM_UNDERDETERMINED, None)`; robustly blamed → `(REJECTED, None, ROBUSTLY_BLAMED)`.

- [ ] **Step 1: Write the failing tests**

Append to `protocol/tests/test_blame_bridge.py`:

```python
from polymer_grammar.status import RejectionReason
from polymer_protocol.blame_bridge import duhem_statuses_from_obstructions


def test_single_cycle_routes_all_members_to_pending_duhem():
    out = duhem_statuses_from_obstructions([_cycle("A", "B", "C")])
    for cid in ("A", "B", "C"):
        assert out[cid] == (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED, None)


def test_shared_claim_routes_to_rejected_robustly_blamed():
    out = duhem_statuses_from_obstructions([_cycle("A", "B", "X"), _cycle("C", "D", "X")])
    assert out["X"] == (Status.REJECTED, None, RejectionReason.ROBUSTLY_BLAMED)
    assert out["A"] == (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED, None)
    assert out["D"] == (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED, None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd protocol && python -m pytest tests/test_blame_bridge.py -k routes -v`
Expected: FAIL with `ImportError: cannot import name 'duhem_statuses_from_obstructions'`.

- [ ] **Step 3: Add the function**

Append to `protocol/src/polymer_protocol/blame_bridge.py`:

```python
from polymer_grammar.blame import duhem_rejection_reason, duhem_status


def duhem_statuses_from_obstructions(
    obstructions: Sequence[Obstruction],
) -> dict[str, tuple[Status, PendingReason | None, RejectionReason | None]]:
    """Per-claim (status, pending_reason, rejection_reason) for every claim implicated by the
    obstructions. Underdetermined -> PENDING duhem_underdetermined; robustly blamed -> REJECTED
    robustly_blamed. Claims not implicated are absent from the dict."""
    verdict = blame_verdict_from_obstructions(obstructions)
    out: dict[str, tuple[Status, PendingReason | None, RejectionReason | None]] = {}
    for cid in sorted(verdict.possibly_blamed):
        mapped = duhem_status(cid, verdict)
        if mapped is None:
            continue
        status, pending_reason = mapped
        out[cid] = (status, pending_reason, duhem_rejection_reason(cid, verdict))
    return out
```

Move the `from polymer_grammar.blame import ...` line to the top import block with the others (keep imports at module top; the inline import above is shown only to mark what the function needs). Final top-of-file grammar import should read:

```python
from polymer_grammar.blame import (
    BlameAssignment,
    BlameSet,
    BlameVerdict,
    duhem_rejection_reason,
    duhem_status,
)
```

- [ ] **Step 4: Export it**

In `protocol/src/polymer_protocol/__init__.py`, add `duhem_statuses_from_obstructions` to the `from .blame_bridge import (...)` block and to `__all__`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd protocol && python -m pytest tests/test_blame_bridge.py -v`
Expected: PASS (all bridge tests).

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/blame_bridge.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_blame_bridge.py
git commit -m "feat(blame-bridge): duhem_statuses_from_obstructions — obstruction cycles to claim statuses"
```

---

### Task 5: Umbrella end-to-end — real SheafStructure → obstructions → statuses

**Files:**
- Test: `tests/test_sheaf_blame_e2e.py` (umbrella-side; numpy available here)

**Interfaces:**
- Consumes: `consistency_report` (from `polymer_claims.sheaf_spectrum`, umbrella/numpy), `duhem_statuses_from_obstructions` (Task 4). This is the second, independent verification route: it drives the *real* numpy frustration detector, not hand-built Obstructions.

- [ ] **Step 1: Inspect an existing sheaf fixture**

Run: `cd /Users/zbb2/Desktop/polymer-claims && python -m pytest tests/test_sheaf_spectrum.py -v 2>&1 | head -20`
Read `tests/test_sheaf_spectrum.py` to copy the exact way it builds a `SheafStructure` with a frustrated cycle (the `SheafVertex`/`SheafEdge` construction and how it calls `consistency_report`). Reuse that construction verbatim in the next step rather than inventing a new one.

- [ ] **Step 2: Write the failing end-to-end test**

Create `tests/test_sheaf_blame_e2e.py` (adapt the `SheafStructure` construction to match the fixture found in Step 1 — the vertices/edges below are the shape; use the real field names from `polymer_protocol.sheaf`):

```python
from polymer_claims.sheaf_spectrum import consistency_report
from polymer_protocol.blame_bridge import duhem_statuses_from_obstructions
from polymer_grammar.status import PendingReason, Status


def test_real_frustrated_cycle_routes_to_pending_duhem(frustrated_triangle):
    # frustrated_triangle: a SheafStructure whose A≈B≈C≈A labels do not close (built as in
    # test_sheaf_spectrum.py). consistency_report runs the numpy detector -> obstructions.
    report = consistency_report(frustrated_triangle)
    assert report.h1_obstructions, "expected at least one H¹ obstruction"
    statuses = duhem_statuses_from_obstructions(report.h1_obstructions)
    assert statuses, "coupling produced no statuses from a real obstruction"
    for _cid, (status, pending_reason, _rej) in statuses.items():
        assert status == Status.PENDING
        assert pending_reason == PendingReason.DUHEM_UNDERDETERMINED
```

Add the `frustrated_triangle` fixture at the top of the file, constructed exactly as the frustrated-cycle case in `test_sheaf_spectrum.py` (Step 1). If that test builds the structure inline rather than via a fixture, inline the same construction here instead of a fixture parameter.

- [ ] **Step 3: Run test to verify it fails (then passes)**

Run: `cd /Users/zbb2/Desktop/polymer-claims && python -m pytest tests/test_sheaf_blame_e2e.py -v`
Expected first run: FAIL only if the fixture construction is wrong — fix the `SheafStructure` construction against Step 1 until the detector returns a non-empty `h1_obstructions`, then the assertions pass. (There is no new production code in this task; it verifies Tasks 2–4 against the real detector.)

- [ ] **Step 4: Run the full suites to confirm nothing regressed**

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims/grammar && python -m pytest -q
cd /Users/zbb2/Desktop/polymer-claims/protocol && python -m pytest -q
cd /Users/zbb2/Desktop/polymer-claims && python -m pytest tests/test_sheaf_spectrum.py tests/test_sheaf_blame_e2e.py -q
```
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tests/test_sheaf_blame_e2e.py
git commit -m "test(blame-bridge): end-to-end real SheafStructure -> obstructions -> PENDING duhem"
```

---

## What this plan deliberately does NOT do (scope guards, from the spec)

- **No general minimal-blame computation** (NP-hard). The bridge supplies only the singleton-per-member candidate and the cross-obstruction intersection. Richer candidate blame-assignments remain the protocol's job to supply to `aggregate_blame` directly.
- **No `run_cycle` mutation.** This plan produces a tested, pure coupling (`duhem_statuses_from_obstructions`) and does not yet wire it into the live corpus fold in `cycle.py`/`corpus.py`. Applying these statuses inside `run_cycle` (demote-not-erase, audit-trail invariant) is the natural follow-up and gets its own plan.
- **No changes to the sheaf math** (`sheaf_spectrum.py` detector is unchanged; we only consume its `Obstruction` output).

## Self-review

- **Spec coverage (item ① done-when):** synthetic frustrated 3-cycle → `BlameSet` whose union is the three ids → PENDING duhem — Task 2 + Task 4. Two overlapping obstructions sharing one claim → that claim ROBUSTLY_BLAMED, others PENDING — Task 3 + Task 4. Grammar purity preserved (no numpy into grammar/protocol) — Global Constraints + bridge lives in pure protocol; verified by Task 5 keeping the numpy call umbrella-side. `test_sheaf.py` + new `test_blame_from_obstruction`-equivalent (`test_blame_bridge.py`) green — Task 5 Step 4.
- **Placeholder scan:** none — every step has concrete code or an exact command. Task 5 Steps 1–2 intentionally direct the implementer to copy the real fixture construction rather than guess field names; that is a lookup instruction, not a placeholder, because the surrounding assertions and imports are concrete.
- **Type consistency:** `duhem_rejection_reason` (Task 1) is consumed in Task 4 with the same signature. `blame_verdict_from_obstructions` (Task 3) is consumed in Task 4. `Obstruction.claim_ids/edges/magnitude` used consistently. `duhem_statuses_from_obstructions` returns the 3-tuple in Tasks 4 and 5 identically.

## Execution note

Ship Tasks 1–4 as the pure, fully-unit-tested coupling; Task 5 is the independent end-to-end check against the real detector and can be skipped only if the numpy `[embed]` extra is unavailable in the environment (note it if so, per the no-silent-caps rule).
