# MDL meta-tier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** A representation revision earns its meta-tier license from the corpus's own compressibility — a pure structural MDL gate + novelty-residual classifier wired into `verify_stage`.

**Architecture:** Branch A (grammar) = new `description_length.py` (the two-part code + `transport` + `mdl_delta`/`novelty_residual`/`clears_mdl_bar`) + `LicenseRoute.MDL_GATE` + extended `meets_meta_tier_bar`. Branch B (protocol) = `verify_stage` tries the MDL route for representation-revisions. Pure/deterministic; grammar ↛ protocol; Corpus stays 4 collections (`Schema` is ephemeral, derived).

**Spec:** `docs/superpowers/specs/2026-06-05-mdl-meta-tier-design.md` (read it — locked choices + gate-policy β).

**Commands (ABSOLUTE paths; Bash cwd persists):** grammar `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q` + `uv run ruff check src tests`; protocol likewise; isolation `cd .../grammar && uv run pytest tests/test_isolation.py -q`.

---

## Branch A — `feat/mdl-meta-tier-grammar`

> `cd /Users/zbb2/Desktop/polymer-claims && git checkout -b feat/mdl-meta-tier-grammar`

### Task 1: the two-part structural description-length code

**Files:** Create `grammar/src/polymer_grammar/description_length.py`; Test `grammar/tests/test_description_length.py`. Export from `grammar/src/polymer_grammar/__init__.py`.

Read first: `claim.py` (Claim fields), `pattern.py` (`PatternRef`/`Pattern.merged_from`), `leaf.py` (`CategoricalLeaf.ontology_term`), `subject.py` (the discriminated kinds incl. `OntologyTermTarget`-style `ontology_term`). The strength axis is `certainty`.

- [ ] **Step 1 — failing tests** for `corpus_implied_schema` + `description_length`:

```python
def test_schema_counts_distinct_patterns_terms():
    # 3 claims: two on pattern P1, one on P2; two distinct categorical ontology terms
    s = corpus_implied_schema(claims)
    assert len(s.patterns) == 2

def test_description_length_is_positive_and_deterministic():
    s = corpus_implied_schema(claims)
    L1 = description_length(claims, s)
    L2 = description_length(claims, s)
    assert L1 == L2 and L1 > 0.0

def test_pattern_selector_is_frequency_weighted():
    # a corpus where all claims share ONE pattern has zero pattern-selector entropy
    # (-log2(1.0) == 0) vs a corpus split across two patterns has > 0
    assert _corpus_code_length(one_pattern_claims, s1) < _corpus_code_length(split_claims, s2) + EPSILON
```

- [ ] **Step 2 — run, confirm fail.**
- [ ] **Step 3 — implement** per spec §"The locked description-length code":
  - Frozen `Schema(patterns: frozenset[tuple[str,str]], terms: frozenset[str], constraints: frozenset[str])` (a `_Model`; tuples/frozensets). `patterns` keyed by `(PatternRef.id, version)`; `terms` = distinct `CategoricalLeaf.ontology_term` + any ontology_term subject ids; `constraints` = `frozenset()` for v1 (no constraint source in object claims yet).
  - `corpus_implied_schema(claims) -> Schema`.
  - `_log_star(n: int) -> float` — Rissanen universal integer code: `log2(2.865) + Σ while log2^k(n) > 0 of that term` (sum the positive iterated logs). For n≤1 return the constant.
  - `_schema_cost(schema) -> float = _log_star(K) + K*_PATTERN_BITS + _log_star(T) + _log_star(C)`.
  - `_corpus_code_length(claims, schema) -> float`: per claim, `-log2(count(pattern)/N)` + for each categorical-leaf/ontology-subject selector `-log2(count(term)/M)` (M = total selector slots) + `_FILL_BITS * n_structural_slots(c)`. Counts from the claim list (pure).
  - `description_length(claims, schema) -> _schema_cost + _corpus_code_length`.
  - Constants `_PATTERN_BITS = 8.0`, `_FILL_BITS = 4.0` (tunable; documented). Guard empty corpus (return 0.0) and freq=0 (skip).
- [ ] **Step 4 — green.**
- [ ] **Step 5 — commit** `feat(grammar): two-part structural description-length code`.

### Task 2: transport + mdl_delta + novelty_residual + clears_mdl_bar

**Files:** Modify `description_length.py`; Test `test_description_length.py`. Import `RepresentationRevision`, `RevisionOperation`, `PatternTarget`, `OntologyTermTarget`, `ConstraintTarget` from `.representation`.

- [ ] **Step 1 — failing tests** (the three diagnostic scenarios from the spec):

```python
def test_redundant_merge_compresses_and_is_consolidation():
    # patterns A,B identical-signature, each used 5x; MERGE(A,B)
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(operation=MERGE, target=PatternTarget(patterns=(refA, refB)), rationale="dup")
    assert mdl_delta(claims, s, rev) < 0.0                  # pays for itself
    assert novelty_residual(claims, s, rev) < EPSILON       # generator-reachable -> consolidation

def test_unused_add_costs_bits():
    rev = RepresentationRevision(operation=ADD, target=PatternTarget(patterns=(refNew,)), rationale="x")
    assert mdl_delta(claims, s, rev) > 0.0                   # pure schema cost, nothing uses it

def test_loadbearing_deprecate_is_rejected():
    # deprecate a specific pattern many claims rely on -> generic re-encoding costs more
    rev = RepresentationRevision(operation=DEPRECATE, target=PatternTarget(patterns=(refSpecific,)), rationale="x")
    assert mdl_delta(claims, s, rev) > 0.0

def test_clears_mdl_bar_threshold():
    assert clears_mdl_bar(-5.0) is True
    assert clears_mdl_bar(-0.0001) is False                  # below _MDL_EPS
```

- [ ] **Step 2 — run, confirm fail.**
- [ ] **Step 3 — implement** per spec §"transport" + §"the gate":
  - `transport(claims, schema, revision) -> (tuple[Claim,...], Schema)`:
    - **MERGE**: build a unified `PatternRef` (deterministic id, e.g. `"merged:" + "+".join(sorted(member ids))`, version `"v1"`); repoint every claim whose `pattern` is a member to the unified ref (`claim.model_copy(update={"pattern": unified})` then `Claim.model_validate(...)` to re-run validators); schema' = schema with members removed + unified added.
    - **ADD**: claims unchanged; schema' = schema with the declared pattern `(id,version)` / term added.
    - **DEPRECATE**: schema' = schema with the target removed; repoint claims using the target pattern to a synthetic generic `PatternRef(id="__generic__", version="v1")` (NOT added to schema.patterns — it is priced via a maximal `_GENERIC_FILL` in `_corpus_code_length`; simplest: give generic-pointed claims an inflated selector by treating `__generic__` as one extra schema pattern with full `_PATTERN_BITS` AND a higher per-claim fill `_GENERIC_FILL_BITS > _FILL_BITS`). Document the device.
    - **RELAX**: return `(tuple(claims), schema)` unchanged (MDL-deferred) → `mdl_delta == 0`.
  - `mdl_delta(claims, schema, revision)`: `c', s' = transport(...)`; `return description_length(c', s') - description_length(claims, schema)`.
  - `novelty_residual(claims, schema, revision) -> float`: sum `_structural_bits(a)` (= `_PATTERN_BITS` for a pattern atom) over schema' atoms NOT generator-reachable from schema. Generator-reachable = the atom is a member-rename or a MERGE-quotient of an existing atom (for MERGE the unified pattern IS a quotient → residual 0). For ADD of a brand-new pattern not derivable from existing → residual `_PATTERN_BITS`. Keep the reachability test explicit and documented.
  - `clears_mdl_bar(mdl_delta, *, eps_bits=_MDL_EPS) -> bool: return mdl_delta < -eps_bits`. `_MDL_EPS = 1.0`.
  - `RevisionDiscovery(_Model)`: `mdl_delta: float`, `novelty_residual: float`, `classification: Literal["discovery","consolidation","rejected"]`; a helper `classify(mdl_delta, residual) -> str`.
- [ ] **Step 4 — green** + full grammar suite + ruff.
- [ ] **Step 5 — commit** `feat(grammar): transport + mdl_delta + novelty_residual for representation revisions`.

### Task 3: LicenseRoute.MDL_GATE + extended meets_meta_tier_bar

**Files:** Modify `grammar/src/polymer_grammar/licensing.py`, `representation.py`; Test `grammar/tests/test_revision.py` (or test_representation).

- [ ] **Step 1 — failing test:**
```python
def test_mdl_gate_route_meets_meta_tier_bar():
    lic = Licensing(route=LicenseRoute.MDL_GATE, satisfactions=(_sat(),),
                    rival_set_closure=RivalSetClosure.ENUMERATED)
    assert meets_meta_tier_bar(lic) is True
    # the existing qualitative route still works; SEVERE_TEST/open still fails
    assert meets_meta_tier_bar(Licensing(route=SEVERE_TEST, satisfactions=(_sat(),),
                                         rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)) is False
```
- [ ] **Step 2 — confirm fail** (MDL_GATE doesn't exist yet).
- [ ] **Step 3 — implement:** add `MDL_GATE = "mdl_gate"` to `LicenseRoute`; update `meets_meta_tier_bar` to `qualitative or licensing.route == LicenseRoute.MDL_GATE`. Update the docstring.
- [ ] **Step 4 — green** + full grammar suite + ruff + isolation.
- [ ] **Step 5 — commit** `feat(grammar): LicenseRoute.MDL_GATE accepted by meets_meta_tier_bar`.

**After 1–3 reviewed:** finish Branch A via superpowers:finishing-a-development-branch (merge local no-ff, no push).

---

## Branch B — `feat/mdl-meta-tier-protocol`

> After A merged: `cd /Users/zbb2/Desktop/polymer-claims && git checkout main && git checkout -b feat/mdl-meta-tier-protocol`

### Task 4: verify_stage tries the MDL route for representation-revisions

**Files:** Modify `protocol/src/polymer_protocol/verify.py`; Test `protocol/tests/test_verify.py` + `protocol/tests/test_cycle.py`.

- [ ] **Step 1 — failing test** (through `run_cycle`):
```python
def test_compressing_representation_revision_licenses_via_mdl():
    # object corpus with two redundant identical-signature patterns A,B used by several claims;
    # a representation-revision claim (with a plan that licenses) carrying MERGE(A,B).
    result = run_cycle(corpus, adapters, ctx)
    rev = result.corpus.by_id()["merge-rev"]
    assert rev.status == Status.LICENSED
    assert rev.licensing.route == LicenseRoute.MDL_GATE

def test_non_compressing_revision_stays_pending():
    # a representation-revision whose MERGE does NOT compress (or an unused ADD) -> held PENDING
    result = run_cycle(corpus2, adapters, ctx)
    assert result.corpus.by_id()["bad-rev"].status == Status.PENDING
```
(Model the satisfied-revision fixture on the #5c meta-tier tests in `test_verify.py`/`test_red_team.py` — a representation-revision that reaches the LICENSED branch needs a plan, selection, execution, satisfaction, grounded membership, BH-bar pass. The strength axis is `certainty`.)

- [ ] **Step 2 — run, confirm fail** (today the revision is held PENDING regardless of compression).
- [ ] **Step 3 — implement** per spec §"Protocol wiring": in the representation-revision branch of `verify_stage`, before the existing `meets_meta_tier_bar` hold, compute `object_claims`, `schema = corpus_implied_schema(object_claims)`, `delta = mdl_delta(object_claims, schema, c.representation_revision)`; if `clears_mdl_bar(delta)`: assemble `Licensing(route=MDL_GATE, satisfactions=(ev.satisfaction,), rival_set_closure=ENUMERATED)`, license via `_with_status`, and (optional) record `RevisionDiscovery` for the audit note; else keep the existing PENDING-hold. Import the description_length functions + `LicenseRoute` from `polymer_grammar`.
- [ ] **Step 4 — green** + full protocol suite + ruff + isolation. Re-run the belief-neutrality test through `run_cycle`.
- [ ] **Step 5 — commit** `feat(protocol): verify_stage licenses compressing representation revisions via MDL_GATE`.

**After 4 reviewed:** finish Branch B (merge local no-ff, no push).

## Self-Review
- Spec coverage: code (T1), transport+deltas+gate+residual (T2), MDL_GATE route (T3), verify wiring (T4). ✓ RELAX-deferred + SELECT-novelty + field-resolved-signature are spec non-goals, not tasks. ✓
- Placeholder scan: every step has concrete formulas/signatures/test scenarios; the generic-pattern device + `_log_star` + the constants are specified. ✓
- Type consistency: `Schema`, `RevisionDiscovery`, `mdl_delta`/`novelty_residual`/`clears_mdl_bar`, `LicenseRoute.MDL_GATE` used identically across tasks. ✓
- Purity/isolation: grammar primitives over `Iterable[Claim]`, no protocol import; Corpus unchanged; `Schema` ephemeral. ✓
