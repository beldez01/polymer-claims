# Typed Causal Roles + Units-of-Measure Algebra (Phase 4 Spec)

Date: 2026-06-01
Status: Phase spec
Refines: `2026-05-31-unified-claim-foundations-spec.md` §3.1 (typed role slots + units-of-measure type system).
Builds on: Phases 1–3 (grammar pkg merged; 68 tests). Uses frozen `_Model`, `Claim`, `QuantityLeaf`.

---

## 0. What this phase is

Two independent capabilities from the syntax layer (§3.1):

1. **Typed causal role slots** — a claim's variables are tagged with their *causal role* (predictor / outcome / confounder / mediator / collider / instrument), and the **adjustment set is derived from the roles, never authored**. Graph position licenses opposite operations: you adjust for confounders, never for mediators (blocks the effect — the Table-2 fallacy) or colliders (opens a spurious path). Pearl's causal-hierarchy discipline, in minimal form.
2. **Units-of-measure algebra** — `Dimension` as an abelian group (base dimensions → integer exponents; multiply = add exponents), making dimensional reasoning decidable (Kennedy 1997; Buckingham Π for free). A quantity leaf may carry a typed `Dimension` alongside its UCUM unit label.

### Scoping decisions (engineering judgment, stated not asked)
- **Roles bind named variables (strings), not ontology subjects.** Full subject/ontology modeling stays a separate later concern; the causal-role logic needs only named variables.
- **Units ships as the `Dimension` algebra + one consumer** (`QuantityLeaf.dimension`). Full UCUM-string→Dimension parsing and the evaluator's compile-time dimensional type-checking land with the **evaluator phase** (where the real consumer is). This phase delivers the *type*, not the parser.

### Success criterion (inherited)
- **Sensitivity:** a claim can express its full causal structure (which variable is a mediator vs a confounder) — distinctions that change what a correct analysis does.
- **Specificity:** the adjustment set *cannot* be hand-authored to include a mediator/collider — the schema forecloses the Table-2 fallacy by construction; and dimensionally incoherent quantities become representable as a *type*, not silently mixed.

---

## 1. Typed causal roles (new module `roles.py`)

```
Role = predictor | outcome | confounder | mediator | collider | instrument

CausalRoles = {
    predictor:   str,                       # exactly one
    outcome:     str,                       # exactly one
    confounders: tuple[str, ...] = (),
    mediators:   tuple[str, ...] = (),
    colliders:   tuple[str, ...] = (),
    instruments: tuple[str, ...] = (),
}
```

### Invariants (model validators)
1. `predictor != outcome`.
2. **Every variable has at most one role** — the six role-sets (incl. the singletons predictor/outcome) are pairwise disjoint. (A variable can't be both a confounder and a mediator; that's a different causal model, authored as such.)

### Derived (not authored)
```
CausalRoles.adjustment_set -> frozenset[str]      #  == frozenset(confounders)
```
- The minimal sufficient adjustment set under correctly-labeled roles is exactly the **confounders**. Mediators, colliders, and instruments are **excluded by construction** — there is no field in which a caller can place a variable into the adjustment set; it is computed.
- A test locks the guarantee: `adjustment_set` is disjoint from `mediators`, `colliders`, and `instruments`, and equals the confounder set.

### Wiring
Add optional, additive `Claim.roles: CausalRoles | None = None` (back-compat: claims without roles still build).

---

## 2. Units-of-measure algebra (new module `units.py`)

```
Dimension = a frozen abelian group over base dimensions
   internal: a normalized mapping {base_name: exponent(int != 0)}   (empty == dimensionless)
   operations:
     a * b     -> Dimension      # exponents added
     a / b     -> Dimension      # exponents subtracted
     a ** n    -> Dimension      # exponents scaled
     a == b                      # same exponent map
     a.is_dimensionless          # empty map
   constructors / constants:
     Dimension.base("length")    # {length: 1}
     DIMENSIONLESS               # {}
```
- Group laws hold: associative, identity = `DIMENSIONLESS`, inverse = `a ** -1`; zero-exponent entries are normalized away so equality is canonical.
- `compatible(a, b)` (== `a == b`) — additive/comparison operations require equal dimensions; this is the decidable "unit mismatch is a type error" check (the *enforcement* against quantity arithmetic is the evaluator phase).

### Wiring (one real consumer)
Add optional, additive `QuantityLeaf.dimension: Dimension | None = None` — a quantity may declare its typed dimension alongside the UCUM `unit` string. No basis tie (a derived quantity can be dimensionless or carry a dimension); UCUM↔Dimension consistency checking is out of scope (needs a parser, deferred).

---

## 3. Module layout (additive)

```
grammar/src/polymer_grammar/
  roles.py    # NEW: Role, CausalRoles (+ adjustment_set)
  units.py    # NEW: Dimension (+ DIMENSIONLESS, ops), compatible
  claim.py    # MODIFY: add roles: CausalRoles | None = None
  leaf.py     # MODIFY: add dimension: Dimension | None = None to QuantityLeaf
  __init__.py # MODIFY: export new names
tests/
  test_roles.py
  test_units.py
  test_claim_roles.py      # wiring + back-compat
  test_leaf_dimension.py   # wiring + back-compat
```

Isolation guard (`test_isolation.py`) still applies.

---

## 4. Acceptance criteria

- `CausalRoles` rejects predictor==outcome and any variable appearing in two roles.
- `adjustment_set` equals the confounder set and is provably disjoint from mediators/colliders/instruments; there is no settable adjustment-set field.
- `Dimension` obeys the abelian-group laws (identity, inverse, associativity, commutativity of `*`), normalizes zero exponents, and `compatible` is equality.
- `Claim.roles` and `QuantityLeaf.dimension` are optional/additive — all 68 prior tests stay green.
- All models frozen + hashable; full suite green; ruff clean; isolation guard passes.

---

## 5. Non-goals (this phase)

- **Not** ontology-backed subjects (roles bind plain variable names).
- **Not** a full causal DAG / back-door algorithm over arbitrary graphs — the minimal sufficient set is read off correctly-labeled roles (a fuller DAG-based derivation can come later if needed).
- **Not** UCUM-string parsing or unit→dimension inference (needs a parser; deferred to the evaluator phase).
- **Not** enforcing dimensional consistency on quantity arithmetic (no arithmetic/evaluator yet — that's Phase 8; this phase ships the *type*).
- **Not** wiring roles into the pattern's `adjustment_role` placeholder (a later reconciliation).

---

## 6. Connections to library

- Realizes unified spec §3.1 (typed role slots + units type system) and the schema-overview "typed role slots, fixed arity" + "units-of-measure type system" rows.
- The derived `adjustment_set` is what the evaluator/protocol will use to forbid hand-authored adjustment (reverse-engineering table, "Role split").
- `Dimension` is the type the evaluator (Phase 8) will enforce against quantity operations and that a future UCUM parser will target.
- Plan: `docs/superpowers/plans/2026-06-01-L2b-roles-and-units.md`.
