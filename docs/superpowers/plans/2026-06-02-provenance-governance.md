# Phase 7 — Provenance + Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the two protocol-imposed metadata objects — `Provenance` (#1: how a claim was generated + priced implicit search) and `Governance` (#3: data hazard + access scope) — as additive-optional `Claim` fields.

**Architecture:** Two small focused modules (`provenance.py`, `governance.py`), each a frozen `_Model` + enums (+ 2 governance helpers), depending only on `base._Model`. Wired as additive-optional `Claim.provenance`/`Claim.governance` (mirrors `subject`/`conclusion`/etc.). The grammar represents; the protocol decides (correction math, SAFETY-GATE, status-setting).

**Tech Stack:** Python 3.12, pydantic v2 (`_Model` frozen + `extra="forbid"`), pytest, uv. Tests: `cd grammar && uv run pytest -q`; lint: `uv run ruff check src tests`.

**Spec:** `docs/superpowers/specs/2026-06-02-provenance-governance-spec.md`

---

## File Structure

- Create: `grammar/src/polymer_grammar/provenance.py` — `GenerationMode` enum + `Provenance` model (+ `agent_generated ⇒ agent_id` validator).
- Create: `grammar/src/polymer_grammar/governance.py` — `HazardClass`/`AccessScope` enums + `Governance` model + `blocks_reproduction`/`requires_safety_review` helpers.
- Create: `grammar/tests/test_provenance.py`, `grammar/tests/test_governance.py`.
- Modify: `grammar/src/polymer_grammar/claim.py` — import both + add `provenance`/`governance` optional fields.
- Modify: `grammar/src/polymer_grammar/__init__.py` — export the public symbols.

Branch `phase7-provenance-governance`; merge `--no-ff` to `main` at the end. Isolation guard stays green (no `polymer_formalclaim`). All module-level imports at TOP (ruff E402, no unused F401).

---

### Task 1: `provenance.py` — GenerationMode + Provenance

**Files:**
- Create: `grammar/src/polymer_grammar/provenance.py`
- Test: `grammar/tests/test_provenance.py`

- [ ] **Step 1: Write the failing test** — create `grammar/tests/test_provenance.py`:

```python
import pytest
from pydantic import ValidationError

from polymer_grammar.provenance import GenerationMode, Provenance


def test_human_authored_provenance_constructs():
    p = Provenance(generated_by=GenerationMode.HUMAN_AUTHORED, search_cardinality=1)
    assert p.generated_by == GenerationMode.HUMAN_AUTHORED
    assert p.search_cardinality == 1
    assert p.agent_id is None
    assert p.preregistration_hash is None


def test_agent_generated_requires_agent_id():
    ok = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="claude-opus-4-8",
                    search_cardinality=40)
    assert ok.agent_id == "claude-opus-4-8"
    with pytest.raises(ValidationError):
        Provenance(generated_by=GenerationMode.AGENT_GENERATED, search_cardinality=40)  # no agent_id


def test_search_cardinality_must_be_at_least_one():
    with pytest.raises(ValidationError):
        Provenance(generated_by=GenerationMode.HUMAN_AUTHORED, search_cardinality=0)


def test_provenance_carries_optional_prereg_hash_and_is_hashable():
    p = Provenance(generated_by=GenerationMode.LITERATURE_EXTRACTED, search_cardinality=1,
                   preregistration_hash="sha256-deadbeef", method="manual-curation")
    assert p.preregistration_hash == "sha256-deadbeef"
    assert isinstance(hash(p), int)
    with pytest.raises(ValidationError):
        Provenance(generated_by=GenerationMode.HUMAN_AUTHORED, search_cardinality=1, bogus=1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_provenance.py -q`
Expected: FAIL (ModuleNotFoundError: No module named 'polymer_grammar.provenance')

- [ ] **Step 3: Write minimal implementation** — create `grammar/src/polymer_grammar/provenance.py`:

```python
"""Provenance — how a claim was generated + the priced implicit search (spec §5 #1).

Without `generated_by` the air-gap / no-self-licensing guarantee can't tell human from
agent; without `search_cardinality` selection-aware significance correction (pricing the
forking paths) is unrepresentable; `preregistration_hash` is the §4 anti-HARKing hash-lock.
The grammar represents; the protocol computes the correction. Imports nothing from
polymer_formalclaim.
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from .base import _Model


class GenerationMode(str, Enum):
    HUMAN_AUTHORED = "human_authored"
    AGENT_GENERATED = "agent_generated"
    LITERATURE_EXTRACTED = "literature_extracted"
    MIGRATED = "migrated"
    IMPORTED = "imported"


class Provenance(_Model):
    generated_by: GenerationMode
    agent_id: str | None = None
    method: str | None = None
    version: str | None = None
    search_cardinality: int = Field(ge=1)        # # hypotheses considered to surface this claim
    preregistration_hash: str | None = None      # hash-lock of the primary test (anti-HARKing)

    @model_validator(mode="after")
    def _agent_needs_id(self) -> "Provenance":
        if self.generated_by == GenerationMode.AGENT_GENERATED and self.agent_id is None:
            raise ValueError("generated_by=agent_generated requires an agent_id")
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_provenance.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/provenance.py grammar/tests/test_provenance.py
git commit -m "feat(grammar): Provenance + GenerationMode (protocol req #1)"
```

---

### Task 2: `governance.py` — HazardClass/AccessScope + Governance + helpers

**Files:**
- Create: `grammar/src/polymer_grammar/governance.py`
- Test: `grammar/tests/test_governance.py`

- [ ] **Step 1: Write the failing test** — create `grammar/tests/test_governance.py`:

```python
import pytest
from pydantic import ValidationError

from polymer_grammar.governance import (
    AccessScope,
    Governance,
    HazardClass,
    blocks_reproduction,
    requires_safety_review,
)


def test_bare_governance_is_public_no_hazard():
    g = Governance()
    assert g.hazard_class == HazardClass.NONE
    assert g.access_scope == AccessScope.PUBLIC
    assert g.note is None


def test_governance_constructs_and_is_hashable():
    g = Governance(hazard_class=HazardClass.DUAL_USE, access_scope=AccessScope.CONTROLLED,
                   note="EGA controlled-access")
    assert g.hazard_class == HazardClass.DUAL_USE
    assert isinstance(hash(g), int)
    with pytest.raises(ValidationError):
        Governance(bogus=1)


def test_blocks_reproduction_over_all_access_scopes():
    expected = {
        AccessScope.PUBLIC: False, AccessScope.REGISTERED_ACCESS: False,
        AccessScope.CONTROLLED: False, AccessScope.RESTRICTED: True, AccessScope.EMBARGOED: True,
    }
    for scope, blocks in expected.items():
        assert blocks_reproduction(Governance(access_scope=scope)) is blocks


def test_requires_safety_review_over_all_hazard_classes():
    expected = {
        HazardClass.NONE: False, HazardClass.LOW: False, HazardClass.MODERATE: False,
        HazardClass.HIGH: True, HazardClass.DUAL_USE: True,
    }
    for hz, review in expected.items():
        assert requires_safety_review(Governance(hazard_class=hz)) is review
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_governance.py -q`
Expected: FAIL (ModuleNotFoundError: No module named 'polymer_grammar.governance')

- [ ] **Step 3: Write minimal implementation** — create `grammar/src/polymer_grammar/governance.py`:

```python
"""Governance — data hazard + access scope of a claim (spec §5 #3).

Claim-level (v1.3 has no per-data-dependency model). Feeds the protocol's SAFETY-GATE
(via requires_safety_review) and the dormant `unreproducible_by_governance` status (via
blocks_reproduction). Load-bearing for the TET2/TCGA controlled-access surface. The grammar
represents the posture; the protocol acts. Imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

from enum import Enum

from .base import _Model


class HazardClass(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    DUAL_USE = "dual_use"


class AccessScope(str, Enum):
    PUBLIC = "public"
    REGISTERED_ACCESS = "registered_access"
    CONTROLLED = "controlled"
    RESTRICTED = "restricted"
    EMBARGOED = "embargoed"


class Governance(_Model):
    hazard_class: HazardClass = HazardClass.NONE
    access_scope: AccessScope = AccessScope.PUBLIC
    note: str | None = None


def blocks_reproduction(governance: Governance) -> bool:
    """True iff the access scope prevents independent reproduction (restricted/embargoed) —
    the protocol uses this to set the `unreproducible_by_governance` PENDING reason."""
    return governance.access_scope in {AccessScope.RESTRICTED, AccessScope.EMBARGOED}


def requires_safety_review(governance: Governance) -> bool:
    """True iff the hazard class warrants the protocol's SAFETY-GATE (high/dual_use)."""
    return governance.hazard_class in {HazardClass.HIGH, HazardClass.DUAL_USE}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_governance.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/governance.py grammar/tests/test_governance.py
git commit -m "feat(grammar): Governance + hazard/access enums + protocol-gate helpers (req #3)"
```

---

### Task 3: Wire `Claim.provenance` + `Claim.governance`

**Files:**
- Modify: `grammar/src/polymer_grammar/claim.py`
- Test: `grammar/tests/test_claim_provenance_governance.py`

- [ ] **Step 1: Write the failing test** — create `grammar/tests/test_claim_provenance_governance.py`:

```python
from polymer_grammar.claim import Claim
from polymer_grammar.governance import AccessScope, Governance, HazardClass
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.provenance import GenerationMode, Provenance
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")


def _claim(**kw):
    base = dict(id="c", title="c", pattern=PatternRef(id="p", version="v1"),
                leaves=(_leaf(),), status=Status.LICENSED)
    base.update(kw)
    return Claim(**base)


def test_claim_carries_provenance_and_governance():
    prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="a1", search_cardinality=12)
    gov = Governance(hazard_class=HazardClass.DUAL_USE, access_scope=AccessScope.CONTROLLED)
    c = _claim(provenance=prov, governance=gov)
    assert c.provenance.search_cardinality == 12
    assert c.governance.hazard_class == HazardClass.DUAL_USE


def test_provenance_and_governance_optional_backcompat():
    c = _claim()
    assert c.provenance is None
    assert c.governance is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_claim_provenance_governance.py -q`
Expected: FAIL (ValidationError: unexpected keyword argument 'provenance')

- [ ] **Step 3: Write minimal implementation** — in `grammar/src/polymer_grammar/claim.py`:
  (a) add these to the relative imports at the top (with the other `from .X import Y` lines):

```python
from .governance import Governance
from .provenance import Provenance
```

  (b) add these two fields to the `Claim` class body, immediately after `subject: Subject | None = None`:

```python
    provenance: Provenance | None = None
    governance: Governance | None = None
```

(No validators — additive/optional, mirroring `subject`/`conclusion`/`licensing`/`roles`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_claim_provenance_governance.py -q`
Expected: PASS (2 passed). Also run `cd grammar && uv run pytest tests/test_claim.py tests/test_claim_subject.py -q` to confirm back-compat.

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/claim.py grammar/tests/test_claim_provenance_governance.py
git commit -m "feat(grammar): additive optional Claim.provenance + Claim.governance"
```

---

### Task 4: Package exports + whole-package verification

**Files:**
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_provenance.py`

- [ ] **Step 1: Write the failing test** — APPEND to `grammar/tests/test_provenance.py`:

```python
def test_public_api_exports():
    import polymer_grammar as pg

    for name in [
        "GenerationMode", "Provenance", "HazardClass", "AccessScope", "Governance",
        "blocks_reproduction", "requires_safety_review",
    ]:
        assert hasattr(pg, name), f"{name} not exported from polymer_grammar"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_provenance.py::test_public_api_exports -q`
Expected: FAIL (AssertionError: GenerationMode not exported from polymer_grammar)

- [ ] **Step 3: Write minimal implementation** — in `grammar/src/polymer_grammar/__init__.py`, ADD a new import block after the existing ones:

```python
from .provenance import GenerationMode, Provenance
from .governance import (
    AccessScope,
    Governance,
    HazardClass,
    blocks_reproduction,
    requires_safety_review,
)
```

And ADD these strings to the `__all__` list (anywhere in the list):

```python
    "GenerationMode",
    "Provenance",
    "AccessScope",
    "Governance",
    "HazardClass",
    "blocks_reproduction",
    "requires_safety_review",
```

- [ ] **Step 4: Run the whole suite + lint**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: PASS — all prior tests (178) + the new provenance/governance/claim tests (11) = 189 green; ruff clean. Confirm `tests/test_isolation.py` passes (no `polymer_formalclaim` import leaked in).

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/__init__.py grammar/tests/test_provenance.py
git commit -m "feat(grammar): export Provenance + Governance public API"
```

---

## Final integration

- [ ] **Merge to main** (no-ff, per project rhythm):

```bash
cd ~/Desktop/polymer-claims
git checkout main
git merge --no-ff phase7-provenance-governance -m "merge: Provenance + Governance (protocol reqs #1 & #3)"
cd grammar && uv run pytest -q   # verify green on the merged result
git branch -d phase7-provenance-governance
```

- [ ] **Update** the Progress Log (below), `docs/superpowers/CONTINUE.md`, the root README, and memory `project_polymer_claims_knowledge_protocol`. Note this advances Phase 7 (§5 #1 + #3 now done; #2 blocked on Phase-8, #5 own phase); the largest re-ingest homeless cluster (premises + provenance metadata) now has a home.

---

## Progress Log

_(Update after every completed task: check the box, note the commit SHA + any decisions.)_

- [ ] Task 1 — provenance.py (GenerationMode + Provenance + agent-id validator)
- [ ] Task 2 — governance.py (enums + Governance + 2 helpers)
- [ ] Task 3 — wire Claim.provenance + Claim.governance (additive)
- [ ] Task 4 — exports + whole-package verify
- [ ] Final — merge to main, docs + memory updated
