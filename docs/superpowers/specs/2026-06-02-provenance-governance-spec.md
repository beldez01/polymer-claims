# Phase 7 — Provenance + Governance (protocol requirements #1 & #3) — design spec

Date: 2026-06-02
Status: design (feeds `writing-plans`)
Requirements: unified spec §5 #1 (`generated_by` + `search_cardinality`) and §5 #3 (`hazard_class` + governance/access-scope)
Depends on: `base._Model`; wires into `claim.Claim`. The re-ingest (`2026-06-02-reingest-findings.md`) showed `premises` + provenance metadata (`posted_at`/`version`/`exp_number`/`notebook`) as the largest homeless cluster — this absorbs that.

## 0. Reading guide

Two additive `Claim` metadata objects the protocol pushes back on the grammar:
- **`Provenance` (#1)** — *how* a claim was generated, and how big the implicit hypothesis search
  was. Without it, "selection-aware significance correction" (pricing the forking paths) is
  unrepresentable, and the air-gap / no-self-licensing guarantee can't tell human from agent.
- **`Governance` (#3)** — the *hazard* and *access scope* of the claim's data. Feeds the protocol's
  SAFETY-GATE and the already-present-but-dormant `unreproducible_by_governance` status. Load-bearing
  for the controlled-access genomic surface (controlled-access genomic data).

The grammar **represents**; the protocol **decides** (computes corrections, runs the safety gate,
sets statuses). Both are additive-optional, frozen, hashable — same discipline as `subject`/etc.

## 1. Goal & scope

Add two small focused modules and wire two optional `Claim` fields:
- `grammar/provenance.py` — `GenerationMode` enum + `Provenance` model.
- `grammar/governance.py` — `HazardClass`/`AccessScope` enums + `Governance` model + 2 helpers.
- `claim.py` — `provenance: Provenance | None = None`, `governance: Governance | None = None`.
- `__init__.py` — export the public symbols.

Frozen `_Model`, no `dict` fields, isolation guard holds. **Out of scope (follow-ups):** per-data-
dependency governance (this is Claim-level); the actual selection-aware correction math + the
SAFETY-GATE stage + auto-setting `unreproducible_by_governance` (all protocol-runtime concerns —
the grammar only represents + exposes the boolean helpers); requirement #2 (oracle, blocked on
Phase-8 `operations`) and #5 (`representation_revision` meta-tier, its own phase).

## 2. `provenance.py` (requirement #1)

```python
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

    # validator: AGENT_GENERATED ⇒ agent_id is present
```

- **`search_cardinality` is required** (`Field(ge=1)`, no default): asserting provenance means
  pricing the implicit search. `1` = a single pre-planned test; `N` = N hypotheses scanned (the
  multiple-comparisons denominator the evaluator uses for selection-aware correction).
- **`preregistration_hash`** is the §4 hash-lock: a content hash of the primary hypothesis pinned
  *before* it was tested. Optional (not every claim is pre-registered); when present it lets the
  protocol prove the primary test wasn't HARKed.
- **Validator** `_agent_needs_id`: if `generated_by == GenerationMode.AGENT_GENERATED` and
  `agent_id is None` → `ValueError`. (An agent-generated claim must name its agent — required for
  the air-gap / no-self-licensing audit; human/literature/migrated/imported modes don't require it.)

## 3. `governance.py` (requirement #3)

```python
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

- Claim-level (v1.3 has no per-data-dependency model; the corpus doesn't need one). Both enum
  fields **default to the benign value** (`none`/`public`) so a bare `Governance()` is a valid
  "public, no hazard" posture.
- The two helpers are pure predicates — the grammar represents the posture; the **protocol** acts
  (sets `unreproducible_by_governance`, runs SAFETY-GATE). No status mutation in the grammar.

## 4. Wiring into Claim

Additive optional, mirroring `subject`/`conclusion`/`licensing`/`roles` (no validator, back-compat):

```python
# claim.py
from .governance import Governance
from .provenance import Provenance
class Claim(_Model):
    ...
    provenance: Provenance | None = None
    governance: Governance | None = None
```

No import cycle: `provenance.py`/`governance.py` import only `.base`; `claim.py` imports them.

## 5. Module boundaries

- `provenance.py` — `GenerationMode` + `Provenance` (+ its validator). Depends only on `base._Model`.
- `governance.py` — `HazardClass` + `AccessScope` + `Governance` + `blocks_reproduction` +
  `requires_safety_review`. Depends only on `base._Model`.
- Two separate modules (distinct concerns: epistemic provenance vs data hazard/access), matching the
  codebase's focused-module convention (`roles.py`, `units.py`).
- Export from `__init__.py`: `GenerationMode`, `Provenance`, `HazardClass`, `AccessScope`,
  `Governance`, `blocks_reproduction`, `requires_safety_review`.

## 6. Testing (TDD)

- `Provenance`: constructs (human + agent with agent_id); `search_cardinality < 1` → ValidationError;
  `agent_generated` without `agent_id` → ValidationError; `agent_generated` WITH `agent_id` → ok;
  `preregistration_hash` optional (defaults None); frozen + hashable.
- `Governance`: bare `Governance()` → `none`/`public`; constructs with each enum; frozen + hashable.
- helpers: `blocks_reproduction` True for restricted/embargoed, False otherwise;
  `requires_safety_review` True for high/dual_use, False otherwise (table over all enum values).
- `Claim`: carries both fields; a Claim without them still constructs and both are `None` (back-compat).
- exports resolve from `polymer_grammar`; isolation guard green.

## 7. Follow-ups (deferred)

- Per-data-dependency governance (currently Claim-level).
- The protocol-runtime consumers: selection-aware correction using `search_cardinality`; the
  SAFETY-GATE stage using `requires_safety_review`; auto-setting `unreproducible_by_governance` from
  `blocks_reproduction`.
- Requirement #2 (oracle credibility — blocked on Phase-8 `operations`) and #5
  (`representation_revision` meta-tier).
- A faithful re-ingest carrying provenance from the v1.2 `premises`/metadata (now representable).
