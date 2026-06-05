# `representation_revision` meta-tier — design spec

> **Status:** approved design, 2026-06-04. The LAST Phase-7 grammar item (§5 #5 of the unified spec) and
> the PREREQUISITE for #5c REPRESENTATION RED-TEAM. Grammar-only slice. Rhythm: this spec → plan
> (writing-plans) → subagent-driven build → merge no-ff → memory.

## What this builds

The **`representation_revision` meta-tier**: the grammar's way to represent a claim *about the IR itself*
— proposing a new pattern, deprecating an ontology term, merging patterns, relaxing a constraint. Per the
unified spec §5.5 + §7: **schema changes are themselves claims**, gated *more conservatively* than
object-level claims, with their own provenance and review ("evolving the grammar is a governed scientific
act, not an edit").

A representation-revision reuses the *entire* `Claim` machinery (status lifecycle, licensing bridge,
provenance, defeat graph, AGM) by carrying one new additive-optional field — the Phase-7 pattern that
landed `subject` / `governance` / `conclusion`. The "meta-tier" is not a parallel type; it is **a claim
that carries a `representation_revision` payload**.

## Resolved forks (from the brainstorm)

- **Representation = an additive `Claim` field** (not a separate top-level model): maximal reuse, faithful
  to "schema changes are themselves claims."
- **Gating = grammar predicate, protocol decides** (not a grammar hard-validator): the grammar ships a
  pure bar-checker + tunable constants; a future protocol slice enforces. Mirrors `governance` / `oracle`.
- **Functorial migration (§7 Spivak Δ/Σ/Π) DEFERRED**: this slice represents *what* revision is proposed;
  executing a migration of existing claims is a separate, bigger concern.

## Context (existing seams)

- **`Claim`** (`grammar/claim.py`): carries additive-optional `subject` / `conclusion` / `governance` /
  `provenance` / `licensing` / `evaluation_plan`, each `X | None = None`, some with a present-only-when-Y
  validator. The `representation_revision` field follows this exact idiom (no status restriction — a
  revision claim is conjectured→licensed like any claim).
- **`Pattern`** (`grammar/pattern.py`): the registry a revision would target. Already carries a
  `merged_from: tuple[str, ...]` field — a fossil of a past representation MERGE. `PatternRef(id, version)`
  is the lightweight reference.
- **`Licensing`** (`grammar/licensing.py`): `route ∈ {SEVERE_TEST, REPLICATION}` (REPLICATION requires ≥2
  distinct materializations) + required `rival_set_closure ∈ {ENUMERATED, ONTOLOGY_BOUNDED,
  OPEN_ACKNOWLEDGED}`. The conservative bar is expressed over these.
- **"grammar represents, protocol decides"**: `governance.requires_safety_review` / `blocks_reproduction`
  and `oracle.cap_strength` all express a rule in the grammar that the protocol enforces. The meta-tier bar
  follows suit.
- **Circular-import discipline**: `claim.py` imports the new `representation.py` for the field type, so
  `representation.py` must not import `claim.py` at module load — the `Claim`-typed helper uses a
  `TYPE_CHECKING` import (the `defeat.py` idiom).

## Component — new module `grammar/src/polymer_grammar/representation.py`

### Operation + target

```python
class RevisionOperation(str, Enum):
    ADD = "add"
    DEPRECATE = "deprecate"
    MERGE = "merge"
    RELAX = "relax"


class PatternTarget(_Model):
    kind: Literal["pattern"] = "pattern"
    patterns: tuple[PatternRef, ...]          # exactly 1 for add/deprecate; >=2 for merge


class OntologyTermTarget(_Model):
    kind: Literal["ontology_term"] = "ontology_term"
    term_id: str = Field(min_length=1)


class ConstraintTarget(_Model):
    kind: Literal["constraint"] = "constraint"
    name: str = Field(min_length=1)


RevisionTarget = Annotated[
    PatternTarget | OntologyTermTarget | ConstraintTarget, Field(discriminator="kind")
]
```

### The revision payload

```python
class RepresentationRevision(_Model):
    operation: RevisionOperation
    target: RevisionTarget
    rationale: str = Field(min_length=1)          # a governed scientific act needs a justification
    proposed_definition: str | None = None        # new pattern/term content as prose/JSON (NOT executable)

    @model_validator(mode="after")
    def _operation_target_compatible(self) -> "RepresentationRevision":
        op, tgt = self.operation, self.target
        if op == RevisionOperation.MERGE:
            if not (isinstance(tgt, PatternTarget) and len(tgt.patterns) >= 2):
                raise ValueError("operation=merge requires a PatternTarget with >=2 patterns")
        elif op == RevisionOperation.RELAX:
            if not isinstance(tgt, ConstraintTarget):
                raise ValueError("operation=relax requires a ConstraintTarget")
        else:  # ADD / DEPRECATE
            if isinstance(tgt, PatternTarget) and len(tgt.patterns) != 1:
                raise ValueError(f"operation={op.value} on a pattern targets exactly 1 pattern")
            if isinstance(tgt, ConstraintTarget):
                raise ValueError(f"operation={op.value} does not apply to a constraint target")
        return self
```

The validator pins the legal (operation, target) pairs: MERGE → PatternTarget(≥2); RELAX → ConstraintTarget;
ADD/DEPRECATE → PatternTarget(exactly 1) or OntologyTermTarget. All models frozen + `extra="forbid"`;
tuples; the whole object is hashable (so a `Claim` carrying it stays content-addressable).

### The conservative bar (grammar represents, protocol decides)

```python
META_TIER_REQUIRED_ROUTE = LicenseRoute.REPLICATION
META_TIER_ALLOWED_CLOSURES = frozenset(
    {RivalSetClosure.ENUMERATED, RivalSetClosure.ONTOLOGY_BOUNDED}
)


def meets_meta_tier_bar(licensing: Licensing) -> bool:
    """The conservative bar a representation-revision's licensing must clear: REPLICATION across independent
    materializations AND a CLOSED rival set (enumerated or ontology-bounded) — never a single severe test
    with an open-acknowledged closure. Pure predicate; the PROTOCOL decides to enforce it (this slice does
    not gate any claim)."""
    return (
        licensing.route == META_TIER_REQUIRED_ROUTE
        and licensing.rival_set_closure in META_TIER_ALLOWED_CLOSURES
    )


def is_representation_revision(claim: "Claim") -> bool:
    """True iff `claim` carries a representation_revision payload (i.e. is a meta-tier claim)."""
    return claim.representation_revision is not None
```

`is_representation_revision` takes a `Claim` via a `TYPE_CHECKING`-only import (avoids the circular import,
mirroring `defeat.py`). `meets_meta_tier_bar` takes a `Licensing` (`licensing.py` does not import
`representation.py`, so a real runtime import is fine).

## Component — wire into `Claim` (`grammar/claim.py`)

Add one additive-optional field (back-compat — defaults None, mirroring `subject`/`governance`):

```python
representation_revision: RepresentationRevision | None = None
```

No present-only-when-Y validator: a representation-revision claim is conjectured→pending→licensed→rejected
like any claim; the meta-ness IS the field, the conservatism IS the bar (`meets_meta_tier_bar`), enforced by
the protocol later. Import `RepresentationRevision` from `.representation` at the top of `claim.py`.

## Scope fences (explicit non-goals)

- **Functorial migration DEFERRED.** No executable migration of existing claims under a licensed revision;
  `proposed_definition` is prose/JSON only. The §7 Spivak Δ/Σ/Π machinery + ontology bindings are a separate
  future slice.
- **Gate ENFORCEMENT is a protocol concern.** This slice ships `is_representation_revision` +
  `meets_meta_tier_bar` + the constants; no claim is auto-gated, no protocol wiring (consistent with
  #5a/#5b — the protocol slice that runs the meta-tier gate, likely alongside #5c/#5d, consumes these).
- **`schema_version` frozen-as-interpreted pinning OUT** (§7) — a separate hardening; not needed for #5c.
- **No reserved meta-pattern forced** on revision claims — the `Claim.pattern` slot stays unconstrained for
  a meta-claim this slice (a registered `representation_revision@v1` meta-pattern is a noted follow-up).
- **Protocol untouched** — this is a pure grammar slice; `Corpus` stays 4 collections.

## Invariants preserved

- One-way isolation: `representation.py` imports `.base`, `.pattern` (PatternRef), `.licensing`
  (Licensing/LicenseRoute/RivalSetClosure), and `Claim` only under `TYPE_CHECKING`. Grammar never imports
  protocol. No new cross-module cycle (`claim.py` → `representation.py` one-way at runtime).
- All new models frozen + `extra="forbid"` + tuples (hashable, content-addressable).
- The new `Claim` field is additive-optional → existing claims/corpora unchanged.
- Exports: add `RevisionOperation`, `PatternTarget`, `OntologyTermTarget`, `ConstraintTarget`,
  `RevisionTarget`, `RepresentationRevision`, `is_representation_revision`, `meets_meta_tier_bar`,
  `META_TIER_REQUIRED_ROUTE`, `META_TIER_ALLOWED_CLOSURES` to `grammar/__init__.py`.

## Testing

**`representation.py`:**
- `RepresentationRevision` builds for each legal (operation, target): ADD pattern(1) / ADD ontology_term /
  DEPRECATE pattern(1) / DEPRECATE ontology_term / MERGE pattern(≥2) / RELAX constraint.
- Validator rejects: MERGE with PatternTarget of 1 / MERGE on a non-pattern target; RELAX on a non-constraint
  target; ADD/DEPRECATE on a constraint; ADD/DEPRECATE on a PatternTarget of ≠1.
- `rationale` empty string rejected (min_length); `term_id`/`name` empty rejected.
- The discriminated `RevisionTarget` dispatches by `kind` (a dict/JSON with `kind="ontology_term"` builds an
  `OntologyTermTarget`); the whole `RepresentationRevision` is hashable (usable in a set).

**`is_representation_revision` / `meets_meta_tier_bar`:**
- `is_representation_revision`: True for a claim carrying the field, False for a plain claim.
- `meets_meta_tier_bar`: REPLICATION+ENUMERATED → True; REPLICATION+ONTOLOGY_BOUNDED → True;
  SEVERE_TEST+ENUMERATED → False; REPLICATION+OPEN_ACKNOWLEDGED → False.

**`Claim` integration:**
- A plain claim has `representation_revision is None` (back-compat).
- A claim carrying a `RepresentationRevision` builds, is hashable, and round-trips `Claim.model_validate`.
- The field is orthogonal to status (a CONJECTURED meta-claim and a LICENSED meta-claim both build).

**Package:**
- All listed symbols import from `polymer_grammar`.

## Files

- Create: `grammar/src/polymer_grammar/representation.py`
- Modify: `grammar/src/polymer_grammar/claim.py` (import + one additive field)
- Modify: `grammar/src/polymer_grammar/__init__.py` (exports)
- Test:   `grammar/tests/test_representation.py` (the module: targets, payload validators, the two helpers)
- Test:   `grammar/tests/test_claim_representation.py` (the additive-field back-compat + meta-claim cases — follows the established per-feature split: `test_claim_subject.py`, `test_claim_licensing.py`, …)
