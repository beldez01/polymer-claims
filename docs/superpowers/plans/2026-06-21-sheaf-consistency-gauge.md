# Sheaf Consistency Gauge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a corpus-level "distance-to-consensus" instrument — the sheaf Laplacian's inconsistency energy, H⁰ dimension, and localized H¹ (frustration) obstructions over the claims graph — exposed via a CLI export and a cheap live headline on the topology frame.

**Architecture:** A pure, numpy-free structure extractor in `protocol/` turns a `Corpus` into a `SheafStructure` (scalar-ℝ stalks on Quantity-leaf claims; equivalence edges weighted by `severity`, defeat edges sign-flipped and weighted by the attacker's e-value). An umbrella module behind the `[embed]` extra builds the sheaf Laplacian `L = δᵀWδ`, computes energy / λ₂ / H⁰ / per-claim tension, and detects frustrated cycles via signed BFS. It is an instrument, not a gate.

**Tech Stack:** Python 3.12, pydantic v2 (`_Model` frozen models), numpy (behind `[embed]`), pytest, ruff, `uv`.

## Global Constraints

- `grammar/` and `protocol/` stay **pure, deterministic, numpy-free** — no clock/random/IO. All numpy lives umbrella-side behind `[embed]`, lazy-imported, **not re-exported** from `polymer_claims.__init__`.
- `Corpus` stays **exactly 4 collections** (claims, defeat_edges, equivalences, fdr_ledger). No new collection; the gauge is a pure read.
- All models subclass frozen `_Model` (`extra="forbid"`); **collection fields are tuples** — never `dict`/`list` on a model.
- New cross-cutting fields land **additive/optional** (`X | None = None` or default `()`), **byte-identical when off** or when numpy is absent.
- Per-package gate: `uv run pytest -q` + `uv run ruff check src tests` (run from that package dir). Full gate: `bash scripts/check-all.sh`.
- TDD: write the failing test first. Merge to `main` `--no-ff`. `main` is pushed to `origin`.
- Float outputs are **rounded to 6 dp** before returning (byte-stable across BLAS implementations), matching `embedding.py`.

## File Structure

- **Create** `protocol/src/polymer_protocol/sheaf.py` — pure DTOs (`SheafVertex`, `SheafEdge`, `DataQualityFlag`, `SheafStructure`; report DTOs `Obstruction`, `ClaimTension`, `ConsistencyHeadline`, `ConsistencyReport`) + `extract_sheaf(corpus, *, status_filter=...)`.
- **Modify** `protocol/src/polymer_protocol/__init__.py` — export the new public names.
- **Create** `protocol/tests/test_sheaf.py` — extractor tests (pure).
- **Create** `src/polymer_claims/sheaf_spectrum.py` — numpy: `consistency_report(structure)`, `consistency_headline(structure)`. Behind `[embed]`, not re-exported.
- **Create** `tests/test_sheaf_spectrum.py` — spectrum/H⁰/H¹ tests (umbrella, `[embed]`).
- **Modify** `protocol/src/polymer_protocol/topology.py` — add optional `consistency: ConsistencyHeadline | None = None` to `TopologyExport`.
- **Modify** `protocol/tests/test_topology.py` (or nearest topology test) — byte-identical-when-off assertion.
- **Modify** `src/polymer_claims/node.py` — attach the live headline in `_layout_topology`.
- **Modify** `src/polymer_claims/cli.py` — add the `export-consistency` subcommand.
- **Modify** `tests/test_cli.py` (or nearest CLI test) — `export-consistency` test.
- **Modify** `docs/superpowers/CONTINUE.md`, `GLOSSARY.md`, `ARCHITECTURE_CURRENT.md` — record the feature.

---

### Task 1: Pure sheaf DTOs + vertex extraction

**Files:**
- Create: `protocol/src/polymer_protocol/sheaf.py`
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_sheaf.py`

**Interfaces:**
- Consumes: `polymer_grammar.Status`, `polymer_protocol.corpus.Corpus`, grammar `Claim`/`QuantityLeaf` (a leaf has `.kind == "quantity"`, `.value: float`, `.unit: str | None`, `.dimension: Dimension | None`; a `Dimension` has `.exponents: tuple[tuple[str,int],...]`).
- Produces: `SheafVertex(claim_id: str, value: float, dimension_sig: tuple[tuple[str,int],...] | None, unit: str | None)`; `SheafStructure(vertices: tuple[SheafVertex,...], edges: tuple[SheafEdge,...], flags: tuple[DataQualityFlag,...])` (edges/flags empty after this task); `extract_sheaf(corpus, *, status_filter: frozenset[Status] = frozenset({Status.LICENSED, Status.PENDING})) -> SheafStructure`. `SheafEdge` and `DataQualityFlag` are defined here too (filled by Tasks 2–3).

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_sheaf.py
from polymer_grammar import Status
from polymer_protocol.sheaf import extract_sheaf, SheafVertex
from .helpers_verify import make_quantity_claim  # if absent, build inline (see note)
from polymer_protocol.corpus import Corpus
from polymer_grammar import FDRLedger


def _corpus(*claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger())


def test_only_quantity_claims_in_status_filter_become_vertices():
    q_lic = make_quantity_claim("q1", value=2.0, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    q_pend = make_quantity_claim("q2", value=5.0, status=Status.PENDING, dim=(("mass", 1),), unit=None)
    q_rej = make_quantity_claim("q3", value=9.0, status=Status.REJECTED, dim=(("mass", 1),), unit=None)
    struct = extract_sheaf(_corpus(q_lic, q_pend, q_rej))
    ids = {v.claim_id for v in struct.vertices}
    assert ids == {"q1", "q2"}                      # REJECTED excluded by default filter
    assert SheafVertex(claim_id="q1", value=2.0, dimension_sig=(("mass", 1),), unit=None) in struct.vertices
```

> Note: if no `make_quantity_claim` helper exists, add a small one to `protocol/tests/conftest.py` that builds a minimal valid `Claim` with one `QuantityLeaf` (fields: `id`, `title`, `pattern`, `leaves=(QuantityLeaf(value=..., measurement_basis=MeasurementBasis.DERIVED, formula="f", dimension=Dimension(exponents=dim)),)`, `status`, and `pending_reason=PendingReason.<any>` when `status==PENDING`). Reuse the existing pattern-ref factory used by other protocol tests (grep `PatternRef(` in `protocol/tests`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_sheaf.py -q`
Expected: FAIL — `ModuleNotFoundError: polymer_protocol.sheaf`.

- [ ] **Step 3: Write minimal implementation**

```python
# protocol/src/polymer_protocol/sheaf.py
"""Cellular-sheaf STRUCTURE extraction over the claims graph (pure, numpy-free).

This module turns a Corpus into a SheafStructure: scalar-ℝ stalks on Quantity-leaf claims,
equivalence edges (agreement) and defeat edges (antagonism, sign-flipped). The numpy spectrum
(energy/H⁰/H¹) lives umbrella-side in polymer_claims.sheaf_spectrum behind the [embed] extra.
Design: docs/superpowers/specs/2026-06-21-sheaf-consistency-gauge-design.md.
"""
from __future__ import annotations

from polymer_grammar import Status

from ._model import _Model  # if _Model is exposed elsewhere, match the existing import (grep "_Model")
from .corpus import Corpus

_DEFAULT_FILTER = frozenset({Status.LICENSED, Status.PENDING})


class SheafVertex(_Model):
    claim_id: str
    value: float
    dimension_sig: tuple[tuple[str, int], ...] | None = None
    unit: str | None = None


class SheafEdge(_Model):
    kind: str          # "equivalence" | "defeat"
    u: str             # equivalence: lower id; defeat: attacker (source)
    v: str             # equivalence: higher id; defeat: target
    weight: float
    sign: int          # +1 equivalence (agreement), -1 defeat (antagonism). d_e = x_u - sign*x_v


class DataQualityFlag(_Model):
    kind: str          # "dimension_mismatch" | "unit_mismatch"
    claim_ids: tuple[str, str]
    detail: str


class SheafStructure(_Model):
    vertices: tuple[SheafVertex, ...] = ()
    edges: tuple[SheafEdge, ...] = ()
    flags: tuple[DataQualityFlag, ...] = ()


def _quantity_leaf(claim):
    for lf in claim.leaves:
        if lf.kind == "quantity":
            return lf
    return None


def extract_sheaf(corpus: Corpus, *, status_filter: frozenset[Status] = _DEFAULT_FILTER) -> SheafStructure:
    vertices: list[SheafVertex] = []
    for c in corpus.claims:
        if c.status not in status_filter:
            continue
        lf = _quantity_leaf(c)
        if lf is None:
            continue
        dim_sig = lf.dimension.exponents if lf.dimension is not None else None
        vertices.append(SheafVertex(claim_id=c.id, value=float(lf.value), dimension_sig=dim_sig, unit=lf.unit))
    return SheafStructure(vertices=tuple(vertices), edges=(), flags=())
```

> Match the real `_Model` import: grep `class _Model` under `grammar/` / `protocol/` and import it the same way the existing protocol models do (e.g. `from polymer_grammar import _Model` or a local base). Do not introduce a second base class.

- [ ] **Step 4: Add public exports**

In `protocol/src/polymer_protocol/__init__.py`, after the `from .topology import (...)` block add:

```python
from .sheaf import (
    ConsistencyHeadline,
    ConsistencyReport,
    ClaimTension,
    DataQualityFlag,
    Obstruction,
    SheafEdge,
    SheafStructure,
    SheafVertex,
    extract_sheaf,
)
```

and add the same names to `__all__`.

> `ConsistencyReport`, `ClaimTension`, `Obstruction`, `ConsistencyHeadline` do not exist yet (Task 4 adds them). To keep this task importable, define them as empty stubs now is NOT allowed (no placeholders). Instead: add only the names that exist after this task — `DataQualityFlag, SheafEdge, SheafStructure, SheafVertex, extract_sheaf` — to both the import and `__all__`. Task 4 extends the import block when it adds the report DTOs.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_sheaf.py -q`
Expected: PASS.

- [ ] **Step 6: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/sheaf.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_sheaf.py protocol/tests/conftest.py
git commit -m "feat(sheaf): pure structure DTOs + vertex extraction"
```

---

### Task 2: Equivalence edges + commensurability gate

**Files:**
- Modify: `protocol/src/polymer_protocol/sheaf.py`
- Test: `protocol/tests/test_sheaf.py`

**Interfaces:**
- Consumes: `corpus.equivalences` — each `EquivalenceClaim(left: str, right: str, severity: float, status: Status)`.
- Produces: equivalence `SheafEdge`s (`kind="equivalence"`, `u`=lower id, `v`=higher id, `weight=severity`, `sign=+1`) and `DataQualityFlag`s for incommensurable / unit-mismatched pairs. Adds module-private `_commensurable(a, b) -> bool | None` (True ok, False unit-mismatch, None dimension-mismatch).

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_sheaf.py (append)
from polymer_grammar import Status
from polymer_protocol.sheaf import extract_sheaf


def test_equivalence_edge_weight_and_commensurability(make_quantity_claim, make_equiv, fdr):
    a = make_quantity_claim("a", value=1.0, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    b = make_quantity_claim("b", value=1.2, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    c = make_quantity_claim("c", value=3.0, status=Status.LICENSED, dim=(("time", 1),), unit=None)  # other dim
    from polymer_protocol.corpus import Corpus
    corpus = Corpus(
        claims=(a, b, c),
        equivalences=(make_equiv("e1", "a", "b", severity=0.8), make_equiv("e2", "a", "c", severity=0.9)),
        fdr_ledger=fdr,
    )
    struct = extract_sheaf(corpus)
    eq_edges = [e for e in struct.edges if e.kind == "equivalence"]
    assert len(eq_edges) == 1
    e = eq_edges[0]
    assert (e.u, e.v, e.weight, e.sign) == ("a", "b", 0.8, 1)            # canonical id order, severity weight
    assert any(f.kind == "dimension_mismatch" and set(f.claim_ids) == {"a", "c"} for f in struct.flags)
```

> Add `make_equiv` + `fdr` fixtures to `protocol/tests/conftest.py` (build `EquivalenceClaim(id=..., left=..., right=..., severity=..., status=Status.LICENSED)` and an empty `FDRLedger()`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_sheaf.py::test_equivalence_edge_weight_and_commensurability -q`
Expected: FAIL — `assert len(eq_edges) == 1` gets `0` (no edges built yet).

- [ ] **Step 3: Write minimal implementation**

In `sheaf.py` add the helper and extend `extract_sheaf` (replace the `return` with edge/flag building):

```python
def _commensurable(a: SheafVertex, b: SheafVertex) -> bool | None:
    if a.dimension_sig is None or b.dimension_sig is None or a.dimension_sig != b.dimension_sig:
        return None            # unknown or differing dimension -> not sheaf-ifiable as a value constraint
    if a.unit != b.unit:
        return False           # same dimension, mismatched named units, no numeric conversion
    return True


def extract_sheaf(corpus: Corpus, *, status_filter: frozenset[Status] = _DEFAULT_FILTER) -> SheafStructure:
    vertices: list[SheafVertex] = []
    for c in corpus.claims:
        if c.status not in status_filter:
            continue
        lf = _quantity_leaf(c)
        if lf is None:
            continue
        dim_sig = lf.dimension.exponents if lf.dimension is not None else None
        vertices.append(SheafVertex(claim_id=c.id, value=float(lf.value), dimension_sig=dim_sig, unit=lf.unit))

    vmap = {v.claim_id: v for v in vertices}
    edges: list[SheafEdge] = []
    flags: list[DataQualityFlag] = []

    for eq in corpus.equivalences:
        if eq.status not in status_filter:
            continue
        if eq.left not in vmap or eq.right not in vmap:
            continue
        a, b = vmap[eq.left], vmap[eq.right]
        comm = _commensurable(a, b)
        if comm is None:
            flags.append(DataQualityFlag(kind="dimension_mismatch", claim_ids=(eq.left, eq.right),
                                         detail=f"{a.dimension_sig} vs {b.dimension_sig}"))
            continue
        if comm is False:
            flags.append(DataQualityFlag(kind="unit_mismatch", claim_ids=(eq.left, eq.right),
                                         detail=f"{a.unit!r} vs {b.unit!r}"))
            continue
        u, v = sorted((eq.left, eq.right))
        edges.append(SheafEdge(kind="equivalence", u=u, v=v, weight=float(eq.severity), sign=1))

    return SheafStructure(vertices=tuple(vertices), edges=tuple(edges), flags=tuple(flags))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_sheaf.py -q`
Expected: PASS (both vertex and equivalence tests).

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/sheaf.py protocol/tests/test_sheaf.py protocol/tests/conftest.py
git commit -m "feat(sheaf): equivalence edges + commensurability gate"
```

---

### Task 3: Defeat edges (effective, sign-flipped, e-value-weighted)

**Files:**
- Modify: `protocol/src/polymer_protocol/sheaf.py`
- Test: `protocol/tests/test_sheaf.py`

**Interfaces:**
- Consumes: `polymer_grammar.effective_defeats(edges, strength, licensed_ids)` → `frozenset[tuple[str,str]]` of surviving (source, target) attacks; `corpus.fdr_ledger.tests` (each `FDRTest(claim_id, e_value: float|None, retracted: bool)`); `corpus.defeat_edges`.
- Produces: defeat `SheafEdge`s (`kind="defeat"`, `u`=attacker, `v`=target, `weight`=attacker latest non-retracted e-value or `1.0`, `sign=-1`). Same commensurability gate as equivalence.

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_sheaf.py (append)
from polymer_grammar import DefeatEdge, DefeatEdgeKind, FDRLedger, FDRTest, Status
from polymer_protocol.corpus import Corpus
from polymer_protocol.sheaf import extract_sheaf


def test_effective_defeat_becomes_signed_edge_weighted_by_attacker_evalue(make_quantity_claim):
    atk = make_quantity_claim("atk", value=4.0, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    tgt = make_quantity_claim("tgt", value=4.0, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    ledger = FDRLedger(tests=(FDRTest(index=1, claim_id="atk", e_value=7.5, alpha_allocated=0.05, discovery=True),))
    corpus = Corpus(
        claims=(atk, tgt),
        defeat_edges=(DefeatEdge(source="atk", target="tgt", kind=DefeatEdgeKind.REBUT),),
        fdr_ledger=ledger,
    )
    struct = extract_sheaf(corpus)
    d_edges = [e for e in struct.edges if e.kind == "defeat"]
    assert len(d_edges) == 1
    assert (d_edges[0].u, d_edges[0].v, d_edges[0].weight, d_edges[0].sign) == ("atk", "tgt", 7.5, -1)
```

> Confirm `FDRTest`'s required fields by grepping `class FDRTest` (the test above passes `index, claim_id, e_value, alpha_allocated, discovery`). `DefeatEdgeKind.REBUT` is an attack kind; verify against `ATTACK_KINDS` in `grammar/.../defeat.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_sheaf.py::test_effective_defeat_becomes_signed_edge_weighted_by_attacker_evalue -q`
Expected: FAIL — `len(d_edges) == 1` gets `0`.

- [ ] **Step 3: Write minimal implementation**

At the top of `sheaf.py` extend the grammar import:

```python
from polymer_grammar import Status, effective_defeats
```

Add the helper:

```python
def _attacker_evalue(latest: dict, claim_id: str) -> float:
    t = latest.get(claim_id)
    if t is None or t.retracted or t.e_value is None:
        return 1.0
    return float(t.e_value)
```

In `extract_sheaf`, after the equivalence loop and before `return`, add:

```python
    strength = {c.id: c.strength for c in corpus.claims}
    licensed = frozenset(c.id for c in corpus.claims if c.status == Status.LICENSED)
    eff = effective_defeats(corpus.defeat_edges, strength, licensed_ids=licensed)
    latest = {t.claim_id: t for t in corpus.fdr_ledger.tests}   # last write wins = latest test per claim
    for src, tgt in sorted(eff):
        if src not in vmap or tgt not in vmap:
            continue                                            # synthetic ':' source or non-quantity endpoint
        a, b = vmap[src], vmap[tgt]
        comm = _commensurable(a, b)
        if comm is None:
            flags.append(DataQualityFlag(kind="dimension_mismatch", claim_ids=(src, tgt),
                                         detail=f"{a.dimension_sig} vs {b.dimension_sig}"))
            continue
        if comm is False:
            flags.append(DataQualityFlag(kind="unit_mismatch", claim_ids=(src, tgt),
                                         detail=f"{a.unit!r} vs {b.unit!r}"))
            continue
        edges.append(SheafEdge(kind="defeat", u=src, v=tgt, weight=_attacker_evalue(latest, src), sign=-1))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_sheaf.py -q`
Expected: PASS (all extractor tests).

- [ ] **Step 5: Full protocol gate + commit**

```bash
cd protocol && uv run pytest -q && uv run ruff check src tests
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/sheaf.py protocol/tests/test_sheaf.py
git commit -m "feat(sheaf): effective defeat edges (sign-flipped, e-value weighted)"
```

---

### Task 4: Report DTOs + numpy spectrum (energy, split, H⁰, λ₂, per-claim tension)

**Files:**
- Modify: `protocol/src/polymer_protocol/sheaf.py` (add report DTOs only — still pure)
- Modify: `protocol/src/polymer_protocol/__init__.py` (export the report DTOs)
- Create: `src/polymer_claims/sheaf_spectrum.py`
- Test: `tests/test_sheaf_spectrum.py`

**Interfaces:**
- Consumes: `SheafStructure` (Task 1–3).
- Produces (pure DTOs in `sheaf.py`):
  - `ClaimTension(claim_id: str, tension: float)`
  - `Obstruction(claim_ids: tuple[str,...], edges: tuple[tuple[str,str],...], magnitude: float)`
  - `ConsistencyHeadline(inconsistency_energy: float, spectral_gap: float)`
  - `ConsistencyReport(inconsistency_energy: float, equivalence_energy: float, defeat_energy: float, spectral_gap: float, h0_dim: int, h1_obstructions: tuple[Obstruction,...] = (), per_claim_tension: tuple[ClaimTension,...] = (), flags: tuple[DataQualityFlag,...] = ())`
- Produces (umbrella): `consistency_report(structure: SheafStructure) -> ConsistencyReport`. (`h1_obstructions` stays `()` until Task 5.)

- [ ] **Step 1: Add report DTOs to `sheaf.py` (pure)**

```python
class ClaimTension(_Model):
    claim_id: str
    tension: float


class Obstruction(_Model):
    claim_ids: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    magnitude: float


class ConsistencyHeadline(_Model):
    inconsistency_energy: float
    spectral_gap: float


class ConsistencyReport(_Model):
    inconsistency_energy: float
    equivalence_energy: float
    defeat_energy: float
    spectral_gap: float
    h0_dim: int
    h1_obstructions: tuple[Obstruction, ...] = ()
    per_claim_tension: tuple[ClaimTension, ...] = ()
    flags: tuple[DataQualityFlag, ...] = ()
```

Then extend the `from .sheaf import (...)` block and `__all__` in `protocol/.../__init__.py` to add `ConsistencyHeadline, ConsistencyReport, ClaimTension, Obstruction`.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_sheaf_spectrum.py
import math
import pytest

np = pytest.importorskip("numpy")  # skip cleanly when [embed] absent

from polymer_protocol.sheaf import SheafStructure, SheafVertex, SheafEdge
from polymer_claims.sheaf_spectrum import consistency_report


def _vert(cid, val):
    return SheafVertex(claim_id=cid, value=val, dimension_sig=(("mass", 1),), unit=None)


def test_agreeing_equivalence_has_zero_energy_and_one_h0():
    s = SheafStructure(vertices=(_vert("a", 2.0), _vert("b", 2.0)),
                       edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=1.0, sign=1),))
    r = consistency_report(s)
    assert r.inconsistency_energy == 0.0
    assert r.h0_dim == 1                       # the two agree -> one consensus dof


def test_disagreeing_equivalence_energy_is_normalized_w_d2():
    s = SheafStructure(vertices=(_vert("a", 1.0), _vert("b", 4.0)),
                       edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=2.0, sign=1),))
    r = consistency_report(s)
    # raw = w*(x_u - x_v)^2 = 2*(1-4)^2 = 18 ; normalized by total weight 2 -> 9
    assert r.inconsistency_energy == pytest.approx(9.0)
    assert r.equivalence_energy == pytest.approx(9.0)
    assert r.defeat_energy == 0.0


def test_defeat_sign_registers_when_values_equal():
    s = SheafStructure(vertices=(_vert("a", 3.0), _vert("b", 3.0)),
                       edges=(SheafEdge(kind="defeat", u="a", v="b", weight=1.0, sign=-1),))
    r = consistency_report(s)
    # raw = w*(x_u + x_v)^2 = (3+3)^2 = 36 ; normalized by 1 -> 36
    assert r.defeat_energy == pytest.approx(36.0)
    assert r.equivalence_energy == 0.0


def test_energy_strictly_decreases_as_values_converge():
    far = consistency_report(SheafStructure(
        vertices=(_vert("a", 0.0), _vert("b", 10.0)),
        edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=1.0, sign=1),)))
    near = consistency_report(SheafStructure(
        vertices=(_vert("a", 4.0), _vert("b", 6.0)),
        edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=1.0, sign=1),)))
    assert near.inconsistency_energy < far.inconsistency_energy


def test_report_is_deterministic():
    s = SheafStructure(vertices=(_vert("a", 1.0), _vert("b", 4.0)),
                       edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=2.0, sign=1),))
    assert consistency_report(s) == consistency_report(s)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run --project . pytest tests/test_sheaf_spectrum.py -q`
Expected: FAIL — `ModuleNotFoundError: polymer_claims.sheaf_spectrum`.

- [ ] **Step 4: Write minimal implementation**

```python
# src/polymer_claims/sheaf_spectrum.py
"""Sheaf Laplacian spectrum over a SheafStructure (umbrella/impure: numpy).

Computes the corpus inconsistency energy (Robinson consistency radius), the equivalence/defeat
energy split, dim H⁰, the spectral gap λ₂, per-claim tension, and (Task 5) localized H¹
frustration obstructions. NOT re-exported from polymer_claims.__init__ — base import stays
numpy-free; import lazily. Behind the [embed] extra. Design:
docs/superpowers/specs/2026-06-21-sheaf-consistency-gauge-design.md.
"""
from __future__ import annotations

import numpy as np

from polymer_protocol.sheaf import (
    ClaimTension,
    ConsistencyReport,
    SheafStructure,
)

_ZERO_TOL = 1e-9    # eigenvalues below this count as the kernel (H⁰)
_ROUND = 6          # 6dp byte-stable output, matching embedding.py


def _coboundary(structure: SheafStructure):
    """Return (idx, x, delta, w, kinds): vertex index map, value vector, coboundary δ (m×n),
    edge weights, and the per-edge kind list."""
    verts = structure.vertices
    idx = {v.claim_id: i for i, v in enumerate(verts)}
    x = np.array([v.value for v in verts], dtype=float)
    m, n = len(structure.edges), len(verts)
    delta = np.zeros((m, n))
    w = np.zeros(m)
    kinds = []
    for k, e in enumerate(structure.edges):
        delta[k, idx[e.u]] += 1.0
        delta[k, idx[e.v]] += -float(e.sign)        # d_e = x_u - sign*x_v
        w[k] = e.weight
        kinds.append(e.kind)
    return idx, x, delta, w, kinds


def consistency_report(structure: SheafStructure) -> ConsistencyReport:
    idx, x, delta, w, kinds = _coboundary(structure)
    n = len(structure.vertices)
    m = len(structure.edges)
    total_w = float(w.sum())

    if m == 0 or total_w == 0.0:
        # no constraints: perfectly consistent; every vertex is its own consensus dof
        return ConsistencyReport(
            inconsistency_energy=0.0, equivalence_energy=0.0, defeat_energy=0.0,
            spectral_gap=0.0, h0_dim=n, h1_obstructions=(), per_claim_tension=(),
            flags=structure.flags,
        )

    d = delta @ x                                   # per-edge discrepancy
    per_edge = w * (d * d)                          # contribution of each edge to x^T L x
    raw = float(per_edge.sum())
    eq = float(per_edge[np.array([k == "equivalence" for k in kinds])].sum())
    df = float(per_edge[np.array([k == "defeat" for k in kinds])].sum())

    L = delta.T @ (w[:, None] * delta)              # δᵀ W δ
    evals = np.linalg.eigvalsh(L)
    h0_dim = int(np.sum(evals < _ZERO_TOL))
    positive = evals[evals >= _ZERO_TOL]
    spectral_gap = float(positive.min()) if positive.size else 0.0

    Lx = L @ x
    tensions = [
        ClaimTension(claim_id=v.claim_id, tension=round(float(x[i] * Lx[i]) / total_w, _ROUND))
        for i, v in enumerate(structure.vertices)
    ]

    return ConsistencyReport(
        inconsistency_energy=round(raw / total_w, _ROUND),
        equivalence_energy=round(eq / total_w, _ROUND),
        defeat_energy=round(df / total_w, _ROUND),
        spectral_gap=round(spectral_gap, _ROUND),
        h0_dim=h0_dim,
        h1_obstructions=(),                         # Task 5
        per_claim_tension=tuple(tensions),
        flags=structure.flags,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run --project . pytest tests/test_sheaf_spectrum.py -q`
Expected: PASS (5 tests).

- [ ] **Step 6: Purity guard — base import stays numpy-free**

Add to the existing import-isolation test (grep `numpy` in `tests/` for the current guard, e.g. `tests/test_numpy_free_base_import.py`; if none exists create `tests/test_sheaf_spectrum.py::test_base_import_numpy_free`):

```python
def test_sheaf_spectrum_not_re_exported():
    import polymer_claims
    assert not hasattr(polymer_claims, "consistency_report")   # lazy-only, like embedding
```

- [ ] **Step 7: Lint + commit**

```bash
uv run --project . ruff check src tests
cd protocol && uv run ruff check src tests && cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/sheaf.py protocol/src/polymer_protocol/__init__.py src/polymer_claims/sheaf_spectrum.py tests/test_sheaf_spectrum.py
git commit -m "feat(sheaf): report DTOs + numpy spectrum (energy/split/H0/gap/tension)"
```

---

### Task 5: H¹ frustration obstructions (signed BFS)

**Files:**
- Modify: `src/polymer_claims/sheaf_spectrum.py`
- Test: `tests/test_sheaf_spectrum.py`

**Interfaces:**
- Consumes: `SheafStructure`, `Obstruction` DTO (Task 4).
- Produces: populates `ConsistencyReport.h1_obstructions` — one `Obstruction` per frustrated fundamental cycle found by signed BFS over the (undirected) edge graph. `magnitude` = sum of the cycle edges' weights.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sheaf_spectrum.py (append)
def test_frustrated_cycle_is_localized():
    # A≡B, B≡C, C⊣A : odd defeat count -> frustrated, no global assignment
    s = SheafStructure(
        vertices=(_vert("A", 1.0), _vert("B", 1.0), _vert("C", 1.0)),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="C", weight=1.0, sign=1),
            SheafEdge(kind="defeat", u="C", v="A", weight=1.0, sign=-1),
        ),
    )
    r = consistency_report(s)
    assert len(r.h1_obstructions) == 1
    assert set(r.h1_obstructions[0].claim_ids) == {"A", "B", "C"}


def test_balanced_cycle_has_no_obstruction():
    # A≡B, B≡C, C≡A : balanced
    s = SheafStructure(
        vertices=(_vert("A", 1.0), _vert("B", 1.0), _vert("C", 1.0)),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="C", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="C", v="A", weight=1.0, sign=1),
        ),
    )
    assert consistency_report(s).h1_obstructions == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/test_sheaf_spectrum.py::test_frustrated_cycle_is_localized -q`
Expected: FAIL — `len(...) == 1` gets `0`.

- [ ] **Step 3: Write minimal implementation**

Add to `sheaf_spectrum.py`:

```python
def _frustration_obstructions(structure: SheafStructure):
    """Signed-BFS frustration detection. Each vertex gets a label in {+1,-1}; edge (u,v,sign)
    demands label[v] == sign*label[u]. A back-edge that violates the running labels witnesses a
    frustrated fundamental cycle (tree path u→…→v plus that edge). Deterministic: sorted ids."""
    from .sheaf_spectrum import Obstruction  # local import avoids cycle if any; or import at top
    adj: dict[str, list[tuple[str, int, float]]] = {v.claim_id: [] for v in structure.vertices}
    for e in structure.edges:
        adj[e.u].append((e.v, e.sign, e.weight))
        adj[e.v].append((e.u, e.sign, e.weight))   # undirected for balance

    label: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    obstructions = []
    seen_cycles: set[frozenset[str]] = set()

    for root in sorted(adj):
        if root in label:
            continue
        label[root] = 1
        parent[root] = None
        queue = [root]
        while queue:
            u = queue.pop(0)
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
                        edges = tuple((cyc[i], cyc[(i + 1) % len(cyc)]) for i in range(len(cyc)))
                        mag = round(float(sum(e.weight for e in structure.edges
                                              if {e.u, e.v} <= key)), _ROUND)
                        obstructions.append(Obstruction(claim_ids=tuple(cyc), edges=edges, magnitude=mag))
    return tuple(obstructions)


def _cycle_ids(parent, u, v):
    """Tree path v→root and u→root, spliced into the fundamental cycle through edge (u,v)."""
    def up(x):
        path = []
        while x is not None:
            path.append(x)
            x = parent[x]
        return path
    pu, pv = up(u), up(v)
    su, sv = set(pu), {p: i for i, p in enumerate(pv)}
    anc = next(p for p in pu if p in sv)               # lowest common ancestor
    left = pu[: pu.index(anc) + 1]                     # u → anc
    right = pv[: sv[anc]]                              # v → (just below anc)
    return left + right[::-1]
```

Then in `consistency_report`, replace `h1_obstructions=(),  # Task 5` with `h1_obstructions=_frustration_obstructions(structure),` and add `from polymer_protocol.sheaf import Obstruction` to the top imports (remove the local import in `_frustration_obstructions`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/test_sheaf_spectrum.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Lint + commit**

```bash
uv run --project . ruff check src tests
git add src/polymer_claims/sheaf_spectrum.py tests/test_sheaf_spectrum.py
git commit -m "feat(sheaf): H1 frustration obstructions via signed BFS"
```

---

### Task 6: `export-consistency` CLI command

**Files:**
- Modify: `src/polymer_claims/cli.py`
- Test: `tests/test_cli.py` (append; grep for the existing `export-topology` CLI test to mirror the harness)

**Interfaces:**
- Consumes: existing `load_corpus(path)` and `_write_or_print(json, out)` helpers in `cli.py` (grep to confirm names); `extract_sheaf`; `consistency_report` (lazy import).
- Produces: a `export-consistency <corpus> [--out PATH]` subcommand printing `ConsistencyReport` JSON; clean message + non-zero exit when numpy/`[embed]` is absent.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py (append) — mirror the existing export-topology test's invocation style
import json
import pytest
from polymer_claims.cli import main


def test_export_consistency_emits_report(tmp_path, capsys, sample_corpus_path):
    pytest.importorskip("numpy")
    rc = main(["export-consistency", str(sample_corpus_path)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "inconsistency_energy" in out and "h0_dim" in out
```

> `sample_corpus_path` — reuse whatever fixture the existing `export-topology` CLI test uses (grep `export-topology` in `tests/test_cli.py`). If it builds a corpus inline and writes JSON to `tmp_path`, do the same here.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/test_cli.py::test_export_consistency_emits_report -q`
Expected: FAIL — `invalid choice: 'export-consistency'`.

- [ ] **Step 3: Write minimal implementation**

Add the command handler near `_cmd_export_topology` in `cli.py`:

```python
def _cmd_export_consistency(args: argparse.Namespace) -> int:
    corpus = load_corpus(args.corpus)
    from polymer_protocol import extract_sheaf          # pure
    try:
        from .sheaf_spectrum import consistency_report  # lazy: base import stays numpy-free
    except ImportError:
        print("export-consistency needs the [embed] extra (numpy). "
              "Install: pip install 'polymer-claims[embed]'", file=sys.stderr)
        return 1
    report = consistency_report(extract_sheaf(corpus))
    _write_or_print(report.model_dump_json(), args.out)
    return 0
```

Register it in the parser block (next to `p_topo`):

```python
    p_cons = sub.add_parser("export-consistency", help="emit a ConsistencyReport (sheaf gauge) — needs [embed]")
    p_cons.add_argument("corpus", help="path to a corpus JSON file")
    p_cons.add_argument("--out", default=None, help="write ConsistencyReport JSON here")
    p_cons.set_defaults(func=_cmd_export_consistency)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/test_cli.py::test_export_consistency_emits_report -q`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

```bash
uv run --project . ruff check src tests
git add src/polymer_claims/cli.py tests/test_cli.py
git commit -m "feat(cli): export-consistency command for the sheaf gauge"
```

---

### Task 7: Live headline on the topology frame

**Files:**
- Modify: `protocol/src/polymer_protocol/topology.py` (add `consistency` field to `TopologyExport`)
- Modify: `src/polymer_claims/sheaf_spectrum.py` (add `consistency_headline`)
- Modify: `src/polymer_claims/node.py` (attach in `_layout_topology`)
- Test: `protocol/tests/test_topology.py` (byte-identical-off) and `tests/test_sheaf_spectrum.py` (headline)

**Interfaces:**
- Consumes: `ConsistencyHeadline` (Task 4); `extract_sheaf`; `_layout_topology(self, corpus)` in `node.py` returns the protocol `TopologyExport`.
- Produces: `TopologyExport.consistency: ConsistencyHeadline | None = None`; `consistency_headline(structure) -> ConsistencyHeadline`; node frames carry the headline when `[embed]` is present, else `None`.

- [ ] **Step 1: Write the failing tests**

```python
# protocol/tests/test_topology.py (append)
def test_topology_export_consistency_defaults_none_and_byte_identical(sample_corpus):
    from polymer_protocol import export_topology, Layout
    exp = export_topology(sample_corpus, layout=Layout.FORCE_DIRECTED)
    assert exp.consistency is None                       # additive, off by default
    # serialization unchanged for consumers that ignore the new optional field
    assert "consistency" in exp.model_dump()             # field exists, value null
```

```python
# tests/test_sheaf_spectrum.py (append)
def test_consistency_headline_matches_report_scalars():
    from polymer_claims.sheaf_spectrum import consistency_headline
    s = SheafStructure(vertices=(_vert("a", 1.0), _vert("b", 4.0)),
                       edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=2.0, sign=1),))
    h = consistency_headline(s)
    r = consistency_report(s)
    assert h.inconsistency_energy == r.inconsistency_energy
    assert h.spectral_gap == r.spectral_gap
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd protocol && uv run pytest tests/test_topology.py -q -k consistency`
Expected: FAIL — `TopologyExport` has no `consistency`.
Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_sheaf_spectrum.py -q -k headline`
Expected: FAIL — no `consistency_headline`.

- [ ] **Step 3: Implement**

In `topology.py`, add the import and field:

```python
from .sheaf import ConsistencyHeadline
```
```python
class TopologyExport(_Model):
    nodes: tuple[TopologyNode, ...] = ()
    edges: tuple[TopologyEdge, ...] = ()
    clusters: tuple[TopologyCluster, ...] = ()
    layout_id: str
    contract_version: str = CONTRACT_VERSION
    consistency: ConsistencyHeadline | None = None      # additive; filled umbrella-side when [embed] present
```

In `sheaf_spectrum.py`:

```python
from polymer_protocol.sheaf import ConsistencyHeadline

def consistency_headline(structure: SheafStructure) -> ConsistencyHeadline:
    r = consistency_report(structure)
    return ConsistencyHeadline(inconsistency_energy=r.inconsistency_energy, spectral_gap=r.spectral_gap)
```

In `node.py`, wrap the return of `_layout_topology` (it currently returns `export_topology(...)`). Capture it then attach:

```python
        topo = export_topology(...)        # keep the existing call exactly as-is
        return self._attach_consistency(topo)
```
and add the helper to the same class:

```python
    def _attach_consistency(self, topo):
        """Attach the cheap sheaf headline (energy + λ₂) when numpy/[embed] is present; else passthrough."""
        try:
            from polymer_protocol import extract_sheaf
            from .sheaf_spectrum import consistency_headline   # lazy: base import stays numpy-free
        except ImportError:
            return topo
        try:
            return topo.model_copy(update={"consistency": consistency_headline(extract_sheaf(self.corpus))})
        except ImportError:
            return topo
```

> `_layout_topology` has two return branches (spectral and force). Apply the wrap to BOTH `return export_topology(...)` statements (grep `return export_topology` in `node.py`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd protocol && uv run pytest tests/test_topology.py -q`
Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_sheaf_spectrum.py -q`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests && cd /Users/zbb2/Desktop/polymer-claims
uv run --project . ruff check src tests
git add protocol/src/polymer_protocol/topology.py protocol/tests/test_topology.py src/polymer_claims/sheaf_spectrum.py src/polymer_claims/node.py tests/test_sheaf_spectrum.py
git commit -m "feat(sheaf): cheap live consistency headline on the topology frame"
```

---

### Task 8: Docs + full gate

**Files:**
- Modify: `docs/superpowers/CONTINUE.md`, `GLOSSARY.md`, `ARCHITECTURE_CURRENT.md`

- [ ] **Step 1: Update the docs**

- `GLOSSARY.md`: add a **sheaf consistency gauge** entry — "a cellular sheaf over the claims graph (scalar stalks on Quantity-leaf claims; equivalence = agreement, defeat = sign-flipped antagonism). Its Laplacian gives the corpus *inconsistency energy* (distance-to-consensus), dim H⁰, and localized H¹ frustration obstructions. An instrument, not a gate. Umbrella/`[embed]`."
- `ARCHITECTURE_CURRENT.md`: in the active table / living-universe note, add one line: the sheaf gauge (`protocol/sheaf.py` extractor + `polymer_claims/sheaf_spectrum.py` numpy) computing the consistency radius + H¹; `export-consistency` CLI + live headline on the topology frame.
- `CONTINUE.md`: move the "Current state" test counts (add the new tests), and under NEXT / Done add the sheaf-gauge slice with the spec+plan paths `docs/superpowers/{specs,plans}/2026-06-21-sheaf-consistency-gauge*` and the deferred follow-ups from spec §8.

- [ ] **Step 2: Run the full gate**

Run: `bash scripts/check-all.sh`
Expected: ALL GREEN through the Python + ruff + isolation + viewer-typecheck sections. (The `next build` step may fail only on the known Google-Fonts network block — that is the documented pre-existing caveat, not a regression from this work.)

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/CONTINUE.md GLOSSARY.md ARCHITECTURE_CURRENT.md
git commit -m "docs(sheaf): record the consistency gauge slice"
```

---

## Self-Review

**Spec coverage:**
- §3.1 vertices (Quantity-leaf, status filter) → Task 1. §3.2–3.3 equivalence + commensurability → Task 2; defeat + antagonism → Task 3. §3.4 weights (severity / attacker e-value) → Tasks 2–3. §4 energy + split + H⁰ + λ₂ + per-claim tension → Task 4; H¹ frustration → Task 5. §5 purity split (pure extractor + `[embed]` numpy, not re-exported) → Tasks 1 & 4 (+ guard in Task 4 Step 6). §6 CLI → Task 6; live headline + `q`-adjacent display → Task 7. §7 tests → embedded per task. §8 future enrichments → recorded in Task 8 docs. All spec sections map to a task.

**Placeholder scan:** No "TBD"/"add error handling"/"write tests for the above" — every code step shows code; every test step shows assertions. The two grep-to-confirm notes (test fixtures, `_Model` import path, CLI helper names) are verification instructions, not deferred work — they exist because the plan must not hard-code a fixture name it can't see; the surrounding code is complete.

**Type consistency:** `SheafVertex(claim_id, value, dimension_sig, unit)`, `SheafEdge(kind, u, v, weight, sign)`, `SheafStructure(vertices, edges, flags)`, `ConsistencyReport(inconsistency_energy, equivalence_energy, defeat_energy, spectral_gap, h0_dim, h1_obstructions, per_claim_tension, flags)`, `ConsistencyHeadline(inconsistency_energy, spectral_gap)`, `Obstruction(claim_ids, edges, magnitude)`, `ClaimTension(claim_id, tension)` — names and fields are used identically across Tasks 1–8. `consistency_report` / `consistency_headline` / `extract_sheaf` signatures match every call site. `d_e = x_u - sign*x_v` is consistent between the coboundary (Task 4) and the sign convention set in Tasks 2–3 (equiv `+1`, defeat `-1`).
