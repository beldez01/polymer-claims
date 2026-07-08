# Duhem Consistency Fold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the item-① H¹→blame coupling into `run_cycle`: a signed-graph frustration obstruction (a coherence contradiction with no local witness) demotes the LICENSED claims it implicates to `PENDING duhem_underdetermined`, reversibly, without touching the FDR ledger.

**Architecture:** Port the numpy-free frustration detector into pure protocol so the cycle can detect obstructions with no numpy. Add a pure, ledger-neutral fold (`apply_duhem_consistency`) that demotes implicated LICENSED claims and reopens resolved ones, mirroring `integrate`'s `_reject`/`_reinstate` shape but writing only claim status (never `D`, never `retract_tests`). Call it in `run_cycle` right after `integrate`, before the survival-credit snapshot.

**Tech Stack:** Python 3, pydantic (frozen `_Model`), pytest. No numpy in protocol.

## Global Constraints

- **Purity:** `polymer_grammar` and `polymer_protocol` stay pure — pydantic + stdlib only, **no numpy**, no `polymer_claims` import. The ported detector and the fold both live in pure protocol.
- **Ledger-neutral (Refund-Validity):** a duhem suspension is *warrant-only* — it does **not** entail any claim's effect-null. Per `refund-validity.md` §6/§8 and `epistemic-core-derivation.pdf` §5, warrant-only defeats de-license in the graph but **leave the `FDRTest` live**. The fold must **not** call `retract_tests` and must **not** mutate `corpus.fdr_ledger`.
- **Demote-only:** the fold never sets `Status.REJECTED`. Only `LICENSED → PENDING duhem_underdetermined` (demote) and `PENDING duhem_underdetermined → PENDING reinstated` (reopen).
- **Determinism:** any ordering from claim ids uses `sorted(...)`.
- **Frozen models:** `Claim`, `Obstruction`, `SheafStructure`, `DuhemFoldAudit` are frozen — build new instances via `model_copy`/`model_validate`, never mutate.
- **Behavior-preserving move:** porting the detector must produce byte-identical obstructions; `tests/test_sheaf_spectrum.py` stays green unchanged.

## File structure

| File | Responsibility | Create/Modify |
|---|---|---|
| `protocol/src/polymer_protocol/sheaf.py` | add public `frustration_obstructions` + `_cycle_ids` (moved from umbrella) | Modify |
| `src/polymer_claims/sheaf_spectrum.py` | delete local detector; import `frustration_obstructions` from protocol | Modify |
| `protocol/src/polymer_protocol/duhem_fold.py` | `DuhemFoldAudit`, `_demote_duhem`, `_reopen_duhem`, `duhem_fold_from_obstructions`, `apply_duhem_consistency` | Create |
| `protocol/src/polymer_protocol/cycle.py` | call `apply_duhem_consistency` after `integrate`, add StageAudit | Modify |
| `protocol/src/polymer_protocol/__init__.py` | export `frustration_obstructions`, `apply_duhem_consistency`, `DuhemFoldAudit` | Modify |
| `protocol/tests/test_frustration_obstructions.py` | numpy-free detector test | Create |
| `protocol/tests/test_duhem_fold.py` | demote / reopen / never-reject / untouched / ledger-unchanged | Create |
| `protocol/tests/test_cycle.py` | integration: frustrated cycle → demote → resolve → reopen | Modify |
| `tests/test_sheaf_spectrum.py` | unchanged; verify still green after the move | (verify only) |

Reference facts (already in the code; do not re-derive):
- `polymer_protocol.sheaf.SheafVertex(claim_id, value, …)`, `SheafEdge(kind, u, v, weight, sign)`, `SheafStructure(vertices, edges, flags)`, `Obstruction(claim_ids: tuple[str,...], edges, magnitude)`.
- `polymer_protocol.sheaf.extract_sheaf(corpus, *, status_filter=frozenset({LICENSED, PENDING})) -> SheafStructure` (pure).
- `polymer_protocol.blame_bridge.blame_verdict_from_obstructions(obstructions) -> BlameVerdict` (item ①); `.possibly_blamed` is the union of implicated ids.
- `polymer_grammar.status.Status`, `PendingReason.DUHEM_UNDERDETERMINED`, `PendingReason.REINSTATED`.
- `integrate.py` pattern: `_reject` builds a new `Claim` via `Claim.model_validate(c.model_copy(update={...}).model_dump())`.

---

### Task 1: Port the frustration detector into pure protocol

**Files:**
- Modify: `protocol/src/polymer_protocol/sheaf.py`
- Modify: `src/polymer_claims/sheaf_spectrum.py`
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_frustration_obstructions.py`

**Interfaces:**
- Produces: `frustration_obstructions(structure: SheafStructure) -> tuple[Obstruction, ...]` in `polymer_protocol.sheaf`, exported from `polymer_protocol`. Private helper `_cycle_ids(parent, u, v)`.

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_frustration_obstructions.py`:

```python
from polymer_protocol.sheaf import SheafEdge, SheafStructure, SheafVertex
from polymer_protocol import frustration_obstructions


def _v(cid):
    return SheafVertex(claim_id=cid, value=0.0)


def _frustrated_triangle():
    # A≡B, B≡C, C⊣A: two agreements + one antagonism = odd signed cycle → frustrated,
    # a contradiction with no local witness. (sign +1 = equivalence, -1 = defeat.)
    return SheafStructure(
        vertices=(_v("A"), _v("B"), _v("C")),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="C", weight=1.0, sign=1),
            SheafEdge(kind="defeat", u="C", v="A", weight=1.0, sign=-1),
        ),
    )


def test_frustrated_triangle_is_one_obstruction_over_all_three():
    obs = frustration_obstructions(_frustrated_triangle())
    assert len(obs) == 1
    assert frozenset(obs[0].claim_ids) == frozenset({"A", "B", "C"})


def test_balanced_cycle_has_no_obstruction():
    # all-equivalence triangle: signed-balanced, not frustrated
    s = SheafStructure(
        vertices=(_v("A"), _v("B"), _v("C")),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="C", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="A", v="C", weight=1.0, sign=1),
        ),
    )
    assert frustration_obstructions(s) == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && python -m pytest tests/test_frustration_obstructions.py -v`
Expected: FAIL with `ImportError: cannot import name 'frustration_obstructions'`.

- [ ] **Step 3: Move the detector into `protocol/src/polymer_protocol/sheaf.py`**

Add near the top of `sheaf.py` (after the existing imports): `from collections import deque`. Add a module constant `_FRUSTRATION_ROUND = 6` (matches the umbrella's `_ROUND`, keeps magnitudes byte-identical). Then append these two functions (copied verbatim from `sheaf_spectrum.py:126-189`, renamed public):

```python
def _cycle_ids(parent: dict, u: str, v: str) -> list[str]:
    """Tree path v→root and u→root, spliced into the fundamental cycle through edge (u,v)."""
    def up(x: str) -> list[str]:
        path = []
        while x is not None:
            path.append(x)
            x = parent[x]
        return path

    pu, pv = up(u), up(v)
    sv = {p: i for i, p in enumerate(pv)}
    anc = next(p for p in pu if p in sv)            # lowest common ancestor
    left = pu[: pu.index(anc) + 1]                  # u → anc (inclusive)
    right = pv[: sv[anc]]                            # v → (just below anc)
    return left + right[::-1]


def frustration_obstructions(structure: SheafStructure) -> tuple[Obstruction, ...]:
    """Signed-BFS frustration detection (pure; no numpy).

    Each vertex gets a label in {+1,-1}; edge (u,v,sign) demands label[v] == sign*label[u].
    A back-edge that violates the running label witnesses a frustrated fundamental cycle
    (tree path u→…→v plus that edge) — a contradiction with no local witness. Deterministic:
    sorted ids.
    """
    adj: dict[str, list[tuple[str, int, float]]] = {v.claim_id: [] for v in structure.vertices}
    for e in structure.edges:
        adj[e.u].append((e.v, e.sign, e.weight))
        adj[e.v].append((e.u, e.sign, e.weight))    # undirected for balance check

    label: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    obstructions: list[Obstruction] = []
    seen_cycles: set[frozenset[str]] = set()

    for root in sorted(adj):
        if root in label:
            continue
        label[root] = 1
        parent[root] = None
        queue: deque[str] = deque([root])
        while queue:
            u = queue.popleft()
            for v, sign, _w in sorted(adj[u]):
                want = sign * label[u]
                if v not in label:
                    label[v] = want
                    parent[v] = u
                    queue.append(v)
                elif label[v] != want:
                    cyc = _cycle_ids(parent, u, v)
                    key = frozenset(cyc)
                    if key not in seen_cycles:
                        seen_cycles.add(key)
                        edges = tuple(
                            (cyc[i], cyc[(i + 1) % len(cyc)]) for i in range(len(cyc))
                        )
                        mag = round(
                            float(sum(e.weight for e in structure.edges if {e.u, e.v} <= key)),
                            _FRUSTRATION_ROUND,
                        )
                        obstructions.append(
                            Obstruction(claim_ids=tuple(cyc), edges=edges, magnitude=mag)
                        )
    return tuple(obstructions)
```

- [ ] **Step 4: Update the umbrella to import, not define**

In `src/polymer_claims/sheaf_spectrum.py`: delete the local `_cycle_ids` (lines 126-140) and `_frustration_obstructions` (lines 143-189). Add `frustration_obstructions` to the existing `from polymer_protocol.sheaf import (...)` block. Change the one call site inside `consistency_report` (it calls `_frustration_obstructions(structure)`) to `frustration_obstructions(structure)`. If `deque` is now unused in `sheaf_spectrum.py`, remove `from collections import deque` (avoid F401).

- [ ] **Step 5: Export from protocol**

In `protocol/src/polymer_protocol/__init__.py`, add `frustration_obstructions` to the `from .sheaf import (...)` block and to `__all__` (next to `extract_sheaf`).

- [ ] **Step 6: Run the protocol test + confirm umbrella unchanged**

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims/protocol && ruff check . && python -m pytest tests/test_frustration_obstructions.py -v
cd /Users/zbb2/Desktop/polymer-claims && python -m pytest tests/test_sheaf_spectrum.py -q
```
Expected: protocol test PASS, ruff clean; `test_sheaf_spectrum.py` PASS unchanged (behavior identical — same function, new home).

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/sheaf.py src/polymer_claims/sheaf_spectrum.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_frustration_obstructions.py
git commit -m "refactor(sheaf): move frustration_obstructions into pure protocol (single source)"
```

**Scope guard:** pure relocation + re-export. Do not alter the algorithm, signs, cycle dedup, or `Obstruction` shape.

---

### Task 2: The fold core — `duhem_fold_from_obstructions`

**Files:**
- Create: `protocol/src/polymer_protocol/duhem_fold.py`
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_duhem_fold.py`

**Interfaces:**
- Produces: `DuhemFoldAudit(_Model)` with `demoted: tuple[str, ...]`, `reopened: tuple[str, ...]`, `contradiction_ids: tuple[str, ...]`.
- Produces: `duhem_fold_from_obstructions(corpus: Corpus, obstructions: Sequence[Obstruction]) -> tuple[Corpus, DuhemFoldAudit]` — pure status logic, ledger untouched.
- Consumes: `blame_verdict_from_obstructions` (item ①), `Claim`, `Status`, `PendingReason`.

- [ ] **Step 1: Write the failing tests**

Create `protocol/tests/test_duhem_fold.py` (reuses the corpus/claim helpers from `protocol/tests/conftest.py` — `make_claim`; read conftest first to match its exact signature, then build LICENSED and PENDING claims by id):

```python
from polymer_grammar import PendingReason, Status
from polymer_protocol.sheaf import Obstruction
from polymer_protocol.corpus import Corpus
from polymer_protocol.duhem_fold import duhem_fold_from_obstructions
from tests.conftest import make_claim   # adjust import to match conftest location


def _obstruction(*ids):
    edges = tuple((ids[i], ids[(i + 1) % len(ids)]) for i in range(len(ids)))
    return Obstruction(claim_ids=tuple(ids), edges=edges, magnitude=1.0)


def _corpus(*claims):
    return Corpus(claims=tuple(claims))


def test_licensed_claim_in_frustrated_cycle_demotes_to_pending_duhem():
    a = make_claim("A", status=Status.LICENSED)
    b = make_claim("B", status=Status.LICENSED)
    c = make_claim("C", status=Status.LICENSED)
    corpus, audit = duhem_fold_from_obstructions(_corpus(a, b, c), [_obstruction("A", "B", "C")])
    by_id = corpus.by_id()
    for cid in ("A", "B", "C"):
        assert by_id[cid].status == Status.PENDING
        assert by_id[cid].pending_reason == PendingReason.DUHEM_UNDERDETERMINED
        assert by_id[cid].licensing is None
    assert set(audit.demoted) == {"A", "B", "C"}
    assert audit.reopened == ()


def test_never_sets_rejected():
    a = make_claim("A", status=Status.LICENSED)
    corpus, _ = duhem_fold_from_obstructions(_corpus(a, make_claim("B", status=Status.LICENSED)),
                                             [_obstruction("A", "B")])
    assert all(c.status != Status.REJECTED for c in corpus.claims)


def test_resolved_cycle_reopens_pending_duhem_to_reinstated():
    # a claim already PENDING duhem from a prior cycle, no longer implicated → reopen
    stuck = make_claim("A", status=Status.PENDING, pending_reason=PendingReason.DUHEM_UNDERDETERMINED)
    corpus, audit = duhem_fold_from_obstructions(_corpus(stuck), [])   # no obstructions now
    assert corpus.by_id()["A"].status == Status.PENDING
    assert corpus.by_id()["A"].pending_reason == PendingReason.REINSTATED
    assert set(audit.reopened) == {"A"}


def test_unimplicated_and_unrelated_claims_untouched():
    lic = make_claim("A", status=Status.LICENSED)                       # licensed, not implicated
    other = make_claim("B", status=Status.PENDING, pending_reason=PendingReason.UNTESTED)
    corpus, audit = duhem_fold_from_obstructions(_corpus(lic, other), [])
    assert corpus.by_id()["A"].status == Status.LICENSED
    assert corpus.by_id()["B"].pending_reason == PendingReason.UNTESTED
    assert audit.demoted == () and audit.reopened == ()


def test_ledger_is_untouched():
    a = make_claim("A", status=Status.LICENSED)
    corpus_in = _corpus(a, make_claim("B", status=Status.LICENSED))
    corpus_out, _ = duhem_fold_from_obstructions(corpus_in, [_obstruction("A", "B")])
    assert corpus_out.fdr_ledger == corpus_in.fdr_ledger   # warrant-only ⇒ no refund
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd protocol && python -m pytest tests/test_duhem_fold.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_protocol.duhem_fold'`.

If `make_claim` does not accept `pending_reason`/`status` kwargs as written, read `protocol/tests/conftest.py` and adapt the calls to its real signature before proceeding — do not change the assertions.

- [ ] **Step 3: Create the module**

Create `protocol/src/polymer_protocol/duhem_fold.py`:

```python
"""Duhem consistency fold: sheaf H¹ frustration obstructions demote the LICENSED claims they
implicate to PENDING duhem_underdetermined, reversibly.

Warrant-only and ledger-neutral: an H¹ contradiction does not entail any claim's effect-null
(Refund-Validity §6/§8; epistemic-core §5), so this de-licenses in the graph but leaves the
FDRTest live — it never calls retract_tests and never mutates fdr_ledger. Demote-only: never
REJECTED. Non-localizable blame (no local witness) → PENDING duhem_underdetermined, not a defeat
edge.
"""
from __future__ import annotations

from collections.abc import Sequence

from polymer_grammar import Claim, PendingReason, Status

from .base import _Model
from .blame_bridge import blame_verdict_from_obstructions
from .corpus import Corpus
from .sheaf import Obstruction, extract_sheaf, frustration_obstructions


class DuhemFoldAudit(_Model):
    demoted: tuple[str, ...] = ()
    reopened: tuple[str, ...] = ()
    contradiction_ids: tuple[str, ...] = ()


def _demote_duhem(c: Claim) -> Claim:
    """LICENSED → PENDING duhem_underdetermined; clear licensing. Mirrors integrate._reject, but
    to PENDING (reversible), not REJECTED. Ledger is not touched (warrant-only)."""
    return Claim.model_validate(
        c.model_copy(
            update={
                "status": Status.PENDING,
                "licensing": None,
                "pending_reason": PendingReason.DUHEM_UNDERDETERMINED,
                "rejection_reason": None,
            }
        ).model_dump()
    )


def _reopen_duhem(c: Claim) -> Claim:
    """A duhem-suspended claim whose cycle has resolved → PENDING reinstated, to re-test. Mirrors
    integrate._reinstate."""
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


def duhem_fold_from_obstructions(
    corpus: Corpus, obstructions: Sequence[Obstruction]
) -> tuple[Corpus, DuhemFoldAudit]:
    """Demote LICENSED claims implicated by any obstruction to PENDING duhem_underdetermined;
    reopen PENDING-duhem claims no longer implicated. Ledger untouched (warrant-only)."""
    implicated = blame_verdict_from_obstructions(obstructions).possibly_blamed
    demoted: list[str] = []
    reopened: list[str] = []
    new_claims: list[Claim] = []
    for c in corpus.claims:
        if c.status == Status.LICENSED and c.id in implicated:
            new_claims.append(_demote_duhem(c))
            demoted.append(c.id)
        elif (
            c.status == Status.PENDING
            and c.pending_reason == PendingReason.DUHEM_UNDERDETERMINED
            and c.id not in implicated
        ):
            new_claims.append(_reopen_duhem(c))
            reopened.append(c.id)
        else:
            new_claims.append(c)
    contradiction_ids = tuple(
        "h1:" + "|".join(sorted(o.claim_ids)) for o in obstructions
    )
    audit = DuhemFoldAudit(
        demoted=tuple(sorted(demoted)),
        reopened=tuple(sorted(reopened)),
        contradiction_ids=tuple(sorted(contradiction_ids)),
    )
    return corpus.model_copy(update={"claims": tuple(new_claims)}), audit


def apply_duhem_consistency(corpus: Corpus) -> tuple[Corpus, DuhemFoldAudit]:
    """Detect frustration obstructions from the corpus's sheaf, then apply the fold. Self-contained
    entry point for run_cycle."""
    obstructions = frustration_obstructions(extract_sheaf(corpus))
    return duhem_fold_from_obstructions(corpus, obstructions)
```

- [ ] **Step 4: Export from protocol**

In `protocol/src/polymer_protocol/__init__.py`, add `apply_duhem_consistency`, `duhem_fold_from_obstructions`, and `DuhemFoldAudit` to a `from .duhem_fold import (...)` block and to `__all__`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd protocol && ruff check . && python -m pytest tests/test_duhem_fold.py -v`
Expected: PASS, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/duhem_fold.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_duhem_fold.py
git commit -m "feat(duhem-fold): ledger-neutral demote/reopen from obstructions + apply_duhem_consistency"
```

**Scope guard:** ledger-neutral (no `retract_tests`, no `fdr_ledger` write); demote-only (never REJECTED); writes only claim status. `apply_duhem_consistency` is a thin detect-then-delegate wrapper (its real-corpus composition is covered by Task 3).

---

### Task 3: Composition test — `apply_duhem_consistency` on a real frustrated corpus

**Files:**
- Test: `protocol/tests/test_duhem_fold.py` (extend)

**Interfaces:**
- Consumes: `apply_duhem_consistency` (Task 2), `extract_sheaf` (proves detection+application compose on a Corpus, not hand-built obstructions).

- [ ] **Step 1: Find the frustrated-corpus construction**

Read `protocol/tests/test_sheaf.py` (and `conftest.py`) to find how a Corpus with Quantity-leaf claims and equivalence/defeat edges that `extract_sheaf` renders as a frustrated cycle is built (A≡B, B≡C, C⊣A over Quantity-leaf claims). Reuse that construction verbatim. If no such corpus fixture exists, build three LICENSED Quantity-leaf claims and add two equivalence relations + one defeat edge forming the odd signed cycle, following `extract_sheaf`'s requirements (only Quantity-leaf, in-status claims become vertices).

- [ ] **Step 2: Write the failing composition test**

Append to `protocol/tests/test_duhem_fold.py` (adapt the corpus construction to Step 1's finding):

```python
from polymer_protocol.duhem_fold import apply_duhem_consistency


def test_apply_duhem_consistency_demotes_on_a_real_frustrated_corpus(frustrated_corpus):
    # frustrated_corpus: LICENSED Quantity-leaf claims A,B,C with A≡B, B≡C, C⊣A (built as in
    # test_sheaf.py). extract_sheaf → frustrated triangle → all three demote.
    corpus, audit = apply_duhem_consistency(frustrated_corpus)
    by_id = corpus.by_id()
    assert set(audit.demoted) == {"A", "B", "C"}
    for cid in ("A", "B", "C"):
        assert by_id[cid].status == Status.PENDING
        assert by_id[cid].pending_reason == PendingReason.DUHEM_UNDERDETERMINED
    assert corpus.fdr_ledger == frustrated_corpus.fdr_ledger   # still ledger-neutral end-to-end
```

Provide `frustrated_corpus` inline (a local variable or fixture) using Step 1's construction. If claim ids differ from A/B/C, assert on the actual ids of the frustrated cycle.

- [ ] **Step 3: Run to verify (fix the construction until it passes)**

Run: `cd protocol && python -m pytest tests/test_duhem_fold.py -k real_frustrated -v`
Expected first: may FAIL if the corpus construction does not produce a frustrated cycle — adjust the edges/signs until `extract_sheaf` yields one obstruction over the three claims (mirror `test_sheaf.py`'s frustrated case), then it passes. No production code changes in this task.

- [ ] **Step 4: Commit**

```bash
git add protocol/tests/test_duhem_fold.py
git commit -m "test(duhem-fold): apply_duhem_consistency composes detection+fold on a real corpus"
```

---

### Task 4: Structural-resolution reopen (demote-effective / reopen-structural)

**Why:** frustration is computed from *effective* defeats (licensed attacker). A demotion de-licenses the cycle members, so their attacks go inert and the *effective* frustration vanishes — a naive "reopen when no longer implicated" would then flap (reopen a claim whose structural contradiction is still present). Fix: **demote** on effective frustration, but **reopen** only when the *structural* signed cycle is gone (a defeat edge actually removed), independent of current licensing.

**Files:**
- Modify: `protocol/src/polymer_protocol/sheaf.py` (add `effective_only` switch to `extract_sheaf`)
- Modify: `protocol/src/polymer_protocol/duhem_fold.py` (fold takes effective + structural obstructions)
- Modify: `protocol/tests/test_duhem_fold.py` (update calls to the new signature; add the structural-stays-put case)

**Interfaces:**
- `extract_sheaf(corpus, *, status_filter=..., effective_only: bool = True) -> SheafStructure`. Default `True` = current behavior (byte-identical). `False` = *structural*: build defeat edges from ALL `corpus.defeat_edges` (skip the `effective_defeats` licensing/dominance filter).
- `duhem_fold_from_obstructions(corpus, effective_obstructions, structural_obstructions) -> tuple[Corpus, DuhemFoldAudit]` — demote on effective, reopen on structural-absence.
- `apply_duhem_consistency(corpus)` computes both and delegates.

- [ ] **Step 1: Add `effective_only` to `extract_sheaf`, test the structural variant**

In `protocol/src/polymer_protocol/sheaf.py`, add the keyword param and branch the defeat-pair source. Change the signature to add `effective_only: bool = True`, and replace the `eff = effective_defeats(...)` line (currently sheaf.py:175-177) with:

```python
    if effective_only:
        defeat_pairs = effective_defeats(
            corpus.defeat_edges, corpus.strength_map(), licensed_ids=corpus.licensed_ids()
        )
    else:
        # structural: every authored defeat edge, regardless of attacker licensing/dominance
        defeat_pairs = {(e.source, e.target) for e in corpus.defeat_edges}
```

Then change the loop header `for src, tgt in sorted(eff):` to `for src, tgt in sorted(defeat_pairs):`. Leave the vmap/commensurable guards and the `SheafEdge(..., sign=-1)` append exactly as they are (structural still only builds edges between actual Quantity-leaf vertices in `status_filter`).

Add to `protocol/tests/test_frustration_obstructions.py` (or a new corpus-level test) a check that a corpus with an odd defeat cycle among **de-licensed (PENDING)** claims yields NO effective obstruction but DOES yield a structural one:

```python
def test_structural_sheaf_sees_delicensed_defeats_effective_does_not():
    # build 3 PENDING Quantity-leaf claims A,B,C with an odd defeat cycle A⊣B⊣C⊣A
    # (construct as in test_duhem_fold's frustrated corpus, but PENDING not LICENSED).
    from polymer_protocol.sheaf import extract_sheaf, frustration_obstructions
    eff = frustration_obstructions(extract_sheaf(pending_odd_cycle_corpus))                 # effective
    struct = frustration_obstructions(extract_sheaf(pending_odd_cycle_corpus, effective_only=False))
    assert eff == ()                       # no licensed attacker → no effective frustration
    assert struct != ()                    # structural cycle still present
```

Build `pending_odd_cycle_corpus` inline following Task 3's construction (read `test_sheaf.py` for the defeat-edge API — `DefeatEdge(kind=REBUT, source=..., target=...)`), but with `status=PENDING` claims and three defeat edges A⊣B, B⊣C, C⊣A (odd). Verify `struct` is non-empty before asserting.

- [ ] **Step 2: Run to verify it fails, then implement**

Run: `cd protocol && python -m pytest tests/test_frustration_obstructions.py -k structural -v` → FAIL (`extract_sheaf` has no `effective_only`). Implement Step 1, re-run → PASS.

- [ ] **Step 3: Rework the fold to demote-effective / reopen-structural**

In `protocol/src/polymer_protocol/duhem_fold.py`, change `duhem_fold_from_obstructions` to take both obstruction sets and key the two branches differently:

```python
def duhem_fold_from_obstructions(
    corpus: Corpus,
    effective_obstructions: Sequence[Obstruction],
    structural_obstructions: Sequence[Obstruction],
) -> tuple[Corpus, DuhemFoldAudit]:
    """Demote LICENSED claims implicated by an EFFECTIVE frustration; reopen PENDING-duhem claims
    no longer in any STRUCTURAL frustration (the contradiction's defeat edges are genuinely gone,
    not merely inert because the claim was suspended)."""
    implicated_eff = blame_verdict_from_obstructions(effective_obstructions).possibly_blamed
    implicated_struct = blame_verdict_from_obstructions(structural_obstructions).possibly_blamed
    demoted: list[str] = []
    reopened: list[str] = []
    new_claims: list[Claim] = []
    for c in corpus.claims:
        if c.status == Status.LICENSED and c.id in implicated_eff:
            new_claims.append(_demote_duhem(c)); demoted.append(c.id)
        elif (
            c.status == Status.PENDING
            and c.pending_reason == PendingReason.DUHEM_UNDERDETERMINED
            and c.id not in implicated_struct
        ):
            new_claims.append(_reopen_duhem(c)); reopened.append(c.id)
        else:
            new_claims.append(c)
    contradiction_ids = tuple("h1:" + "|".join(sorted(o.claim_ids)) for o in effective_obstructions)
    audit = DuhemFoldAudit(
        demoted=tuple(sorted(demoted)),
        reopened=tuple(sorted(reopened)),
        contradiction_ids=tuple(sorted(contradiction_ids)),
    )
    return corpus.model_copy(update={"claims": tuple(new_claims)}), audit
```

(Note: `implicated_eff ⊆ implicated_struct` since effective defeats are a subset of structural ones, so a freshly-demoted claim is in `implicated_struct` and cannot be reopened in the same call — mutual exclusivity preserved.)

Update `apply_duhem_consistency`:

```python
def apply_duhem_consistency(corpus: Corpus) -> tuple[Corpus, DuhemFoldAudit]:
    effective = frustration_obstructions(extract_sheaf(corpus))
    structural = frustration_obstructions(extract_sheaf(corpus, effective_only=False))
    return duhem_fold_from_obstructions(corpus, effective, structural)
```

- [ ] **Step 4: Update the fold tests to the new signature**

In `protocol/tests/test_duhem_fold.py`, update each `duhem_fold_from_obstructions(corpus, X)` call to pass both sets:
- demote tests: `duhem_fold_from_obstructions(corpus, [obs], [obs])`.
- ledger test: `duhem_fold_from_obstructions(corpus, [obs], [obs])`.
- the reopen test (`test_resolved_cycle_reopens...`): `duhem_fold_from_obstructions(corpus, [], [])` — structural empty ⇒ reopen fires.

Add a NEW test for the structural-stays-put case (this is the branch the Task-2 review flagged as untested, now meaningful):

```python
def test_pending_duhem_stays_put_while_structurally_implicated():
    stuck = make_claim("A", status=Status.PENDING, pending_reason=PendingReason.DUHEM_UNDERDETERMINED)
    corpus, audit = duhem_fold_from_obstructions(_corpus(stuck), [], [_obstruction("A", "B", "A")])
    # effective empty (no demote), but A still in a STRUCTURAL cycle → NOT reopened
    assert corpus.by_id()["A"].pending_reason == PendingReason.DUHEM_UNDERDETERMINED
    assert audit.reopened == ()
```

(Use a structural obstruction whose `claim_ids` include "A"; adjust the tuple to a valid obstruction over ≥2 ids that contains "A".)

- [ ] **Step 5: Run the fold + detector suites**

Run: `cd protocol && ruff check . && python -m pytest tests/test_duhem_fold.py tests/test_frustration_obstructions.py -v`
All green, ruff clean. Also run `python -m pytest tests/test_sheaf.py -q` and `cd /Users/zbb2/Desktop/polymer-claims && python -m pytest tests/test_sheaf_spectrum.py -q` to confirm the `extract_sheaf` change (default `effective_only=True`) left existing sheaf behavior byte-identical.

- [ ] **Step 6: Commit**

```bash
git add protocol/src/polymer_protocol/sheaf.py protocol/src/polymer_protocol/duhem_fold.py protocol/tests/test_duhem_fold.py protocol/tests/test_frustration_obstructions.py
git commit -m "feat(duhem-fold): structural-resolution reopen (demote effective, reopen when structural cycle gone)"
```

**Scope guard:** `effective_only` defaults `True` (existing callers unaffected). Reopen keys on structural absence; demote on effective presence. Still ledger-neutral, still demote-only.

---

### Task 5: Wire into `run_cycle` + empirically confirm the demote fires

**Files:**
- Modify: `protocol/src/polymer_protocol/cycle.py`
- Test: `protocol/tests/test_cycle.py`

**Interfaces:** Consumes `apply_duhem_consistency` (Task 4). Adds one `StageAudit` stage `"duhem_consistency"`.

**The load-bearing empirical question:** the demote fires only if `integrate` leaves the frustrated (freshly-licensed) odd-cycle claims `LICENSED` (they are not in `prior_in`, so `flipped_out` should exclude them — but this MUST be confirmed against the real `integrate`/`restore_consistency`, not assumed). Step 1's test is the confirmation. **If the claims are NOT `LICENSED` after `integrate` (integrate strips them first), STOP and report DONE_WITH_CONCERNS** — that means the fold must move *inside* integrate's undecided-set handling (reclassify undecided-cycle members from REJECTED to PENDING duhem) rather than run as a post-integrate pass, which is a redesign, not a fix to bury here.

- [ ] **Step 1: Add the integration test (demote → structural resolve → reopen)**

Read `protocol/tests/test_cycle.py` for the `run_cycle` call and its adapters/ctx fixtures. Build a corpus with **three LICENSED Quantity-leaf claims A,B,C and an odd defeat cycle A⊣B, B⊣C, C⊣A** (REBUT edges; odd count frustrates). Drive one cycle and assert the members demote; then remove one defeat edge (structural resolution) and drive again, asserting reopen:

```python
def test_run_cycle_demotes_odd_defeat_cycle_then_reopens_on_structural_resolution(...):
    result = run_cycle(odd_cycle_corpus, adapters, ctx, ...)
    by_id = result.corpus.by_id()
    demoted = [cid for cid in ("A", "B", "C")
               if by_id[cid].pending_reason == PendingReason.DUHEM_UNDERDETERMINED]
    # If this assert fails because the claims are REJECTED/absent, integrate stripped them first:
    # STOP and report DONE_WITH_CONCERNS (fold must move inside integrate) — do not force the test.
    assert demoted, "odd defeat cycle among licensed claims should demote to PENDING duhem"
    assert any(a.stage == "duhem_consistency" and a.count > 0 for a in result.audit)

    # remove ONE defeat edge → structural cycle broken → reopen next cycle
    remaining = tuple(e for e in result.corpus.defeat_edges if not (e.source == "C" and e.target == "A"))
    resolved = result.corpus.model_copy(update={"defeat_edges": remaining})
    result2 = run_cycle(resolved, adapters, ctx, ...)
    assert result2.corpus.by_id()["A"].pending_reason == PendingReason.REINSTATED
```

Adapt fixtures/ids to `test_cycle.py`'s helpers. Before the demote assert, it is fine to assert the `duhem_consistency` stage exists so a wiring failure is distinguishable from an integrate-interaction failure.

- [ ] **Step 2: Run to verify it fails**

Run: `cd protocol && python -m pytest tests/test_cycle.py -k odd_defeat_cycle -v`
Expected: FAIL — no `duhem_consistency` stage yet.

- [ ] **Step 3: Wire the fold into `run_cycle`**

In `protocol/src/polymer_protocol/cycle.py`, immediately after the `integrate(...)` call and its `StageAudit.append` (the block ending near line 183) and **before** the survival-credit snapshot comment (`# Credit is allocated on SURVIVAL`, ~line 185), insert:

```python
    corpus, duhem_audit = apply_duhem_consistency(corpus)
    audit.append(StageAudit(
        stage="duhem_consistency",
        note=f"{len(duhem_audit.demoted)} demoted (duhem), {len(duhem_audit.reopened)} reopened"
             + (f"; {sorted(duhem_audit.contradiction_ids)}" if duhem_audit.contradiction_ids else ""),
        count=len(duhem_audit.demoted),
    ))
```

Add `from .duhem_fold import apply_duhem_consistency` to the module imports. Placing it here (pre-credit-snapshot) means a demoted claim earns no survival credit this cycle — symmetric with AGM-retracted claims (the snapshot reads `after[cid].status == Status.LICENSED`).

- [ ] **Step 4: Run the test + full protocol suite**

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims/protocol && ruff check . && python -m pytest tests/test_cycle.py -q && python -m pytest -q
```
Expected: the new test passes; the full protocol suite stays green (the fold is a no-op on corpora with no frustrated cycle). If the demote assert fails per Step 1's guard, report DONE_WITH_CONCERNS with the observed post-integrate statuses.

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/cycle.py protocol/tests/test_cycle.py
git commit -m "feat(cycle): apply duhem consistency fold after integrate (demote-only, ledger-neutral)"
```

**Scope guard:** one call site + one StageAudit, after integrate, before the credit snapshot. No reordering of existing phases; no signature change to `run_cycle`.

---

## Self-review

- **Spec coverage:** §3 detector port → Task 1; §4 fold (demote/ledger-neutral/never-reject) → Task 2 + its tests; §4 `apply_duhem_consistency` real-corpus composition → Task 3; §4/§8 **structural-resolution reopen** (the correction: demote on effective frustration, reopen only when the structural cycle is gone) → Task 4; §5 run_cycle wiring + StageAudit + ordering-before-credit → Task 5. §8 ledger-unchanged → Task 2 `test_ledger_is_untouched` + Task 3 end-to-end check.
- **The load-bearing risk, made explicit:** whether the demote fires through `run_cycle` depends on `integrate` leaving freshly-licensed odd-cycle claims `LICENSED` (they are not in `prior_in`, so `flipped_out` should exclude them). This is confirmed empirically by Task 5 Step 1, NOT assumed — with an explicit STOP-and-report guard if `integrate` strips them first (which would mean the fold must move inside integrate's undecided-set handling, a redesign). This is the single place the whole wiring could be a no-op, so it is verified by a second route (a live cycle), not by static reasoning.
- **Placeholder scan:** none — code is complete. Task 3 Step 1, Task 4 Step 1, and Task 5 Step 1 are read-the-fixture-then-build instructions (the odd-defeat-cycle corpus), with concrete assertions and an explicit finding-guard around them — the same pattern used for the item-① e2e fixture, not a placeholder.
- **Type consistency:** `DuhemFoldAudit` fields used identically across Tasks 2–5; `duhem_fold_from_obstructions` takes `(corpus, effective_obstructions, structural_obstructions)` consistently after Task 4; `apply_duhem_consistency(corpus)` signature matches its Task-5 call site; `extract_sheaf`'s new `effective_only` kw defaults `True` (existing callers unaffected).

## Execution note

Tasks 1–3 are the pure building blocks, fully unit-tested. Task 4 is the correctness rework (structural reopen) driven by the effective-vs-structural frustration distinction. Task 5 is the live wiring and is the one place a hidden `integrate` interaction could make the fold a no-op — its integration test is written to *surface that as a finding* (DONE_WITH_CONCERNS) rather than pass hollow, so a real no-op cannot masquerade as success.
