# MDL gate + novelty residual for the representation-revision meta-tier — Design

**Date:** 2026-06-05
**Status:** Approved (three description-length choices locked by the user; gate-policy β flagged inline).
**Motivation:** Wang & Buehler, *Self-Revising Discovery Systems for Science* (arXiv:2606.01444, 2026)
independently formalize discovery as a **verified schema expansion** gated by description length (MDL),
with novelty measured as a **pointwise residual** beyond functorial (Left Kan) transport. This spec ports
those two ideas into our already-built `representation_revision` meta-tier: a representation revision earns
its license from the corpus's **own compressibility**, and its novelty is measured objectively — replacing
our current qualitative REPLICATION-count bar with a quantitative, corpus-computed one.

This is consistent with our verification philosophy ([[project_polymer_claims_verification_philosophy]]):
the revision is *earned from its own data* (the corpus it re-expresses), not from internal consistency.

---

## What we are NOT doing (honest scope)

We port the **idea**, not the category theory. `transport` is a deterministic structural rewrite (the
Left-Kan analog); our description length is a **structural / representational** two-part code over the typed
claim corpus — NOT copresheaves/Kan extensions over a base category, and NOT predictive-model compression of
raw experimental data. W&B compress raw evidence because their claims *are* fitted models; our claims are
typed assertions, so we score *representational parsimony* (does this schema express the corpus of claims
compactly). If the categorical formalism is ever wanted for a paper, it bolts on top — `transport` /
`novelty_residual` are exactly the comparison map they formalize.

---

## The locked description-length code (the foundation)

`L(claims, schema) = L_schema(schema) + L_corpus(claims, schema)` — a two-part structural MDL code. The
**schema is explicit** (a derived, ephemeral value — NOT a 5th Corpus collection), so ADD/DEPRECATE of a
declared-but-unused atom is priced correctly.

### Choice 1 — structural granularity (LOCKED)
Encode the structural skeleton only: which pattern, which slot-*types*, which ontology-term selectors. Raw
quantity values are a fixed per-slot cost (`_FILL_BITS`) that **cancels in every `mdl_delta`** (included so
`L` is a complete code, never compared in isolation).

### Choice 2 — corpus-relative ontology cost (LOCKED)
Every ontology/categorical selector is priced by its **empirical frequency in the corpus**, `−log2(freq)` —
NOT the external ontology cardinality. Self-contained, pure, no IO.

### Choice 3 — `log*` for schema-size counts (LOCKED)
Schema-size integers (number of patterns / terms / constraints) use Rissanen's universal code
`log*(n) = log2(c) + log2(n) + log2(log2 n) + …` (positive terms only), so counts are honest prefix-code bits.

### `L_schema(schema)`
```
L_schema = log*(K) + K · _PATTERN_BITS          # K distinct patterns; fixed per-pattern table cost
         + log*(T)                               # T distinct ontology terms committed to (flat structural)
         + log*(C)                               # C distinct named constraints
```
- `_PATTERN_BITS` = a fixed module constant (tunable). v1 uses a flat per-pattern cost so a MERGE's schema
  saving is exactly `_PATTERN_BITS` per pattern removed. (A field-resolved pattern signature — cost by
  `estimand`/`scale`/`invariance_group` content — is a documented future refinement.)

### `L_corpus(claims, schema)`
```
L_corpus = Σ_{claim c}[  −log2(freq_pattern(c))                         # name c's pattern, frequency-weighted
                       + Σ_{categorical leaf / ontology_term subject s} −log2(freq_term(s))   # term selectors
                       + _FILL_BITS · n_structural_slots(c) ]            # fixed; cancels in the delta
```
- `freq_pattern(c) = count(pattern of c) / N`. The pattern-selector total is `N·H(pattern distribution)` —
  the term that makes MERGE pay off.
- `freq_term(s) = count(term) / (total term-selector slots)`, corpus-relative.

`description_length(claims, schema)` is **pure** (frequencies from the frozen corpus; `log2`/`log*`
deterministic; no IO/clock/random), **complete** (finite length per claim), and **delta-meaningful**.

---

## `transport` — the structural rewrite (Left-Kan analog), per operation

`transport(claims, schema, revision) -> (claims', schema')`. Deterministic; pure. The "current schema" at
adjudication time = `corpus_implied_schema(object_claims)` (object_claims = claims WITHOUT a
representation_revision payload).

- **MERGE** (PatternTarget, ≥2 patterns): schema' replaces the ≥2 member patterns with one unified
  `PatternRef` (deterministic id; the IR's `Pattern.merged_from` records the members). Every object claim
  using any member is repointed to the unified ref. Unified signature is one pattern-table entry. → schema
  loses (members−1) pattern entries; the pattern-selector entropy drops as the members' frequencies coalesce.
- **ADD** (PatternTarget of 1, or OntologyTermTarget): schema' gains the declared atom; **no claim is
  repointed** (existing claims don't auto-migrate). → `L_schema` rises by the atom's cost, `L_corpus`
  unchanged → `mdl_delta > 0` unless something already uses it. Correct: a new pattern earns its MDL license
  only once claims actually accumulate under it (until then it routes to the qualitative bar).
- **DEPRECATE** (PatternTarget of 1, or OntologyTermTarget): schema' drops the target atom; object claims
  using it are repointed to a synthetic **generic** pattern (maximal signature, internal to the code).
  Deprecating an unused/redundant atom → `mdl_delta < 0`; deprecating a load-bearing specific pattern raises
  every dependent claim's encoding cost (generic is less compact) → `mdl_delta > 0`, rejected. Correct.
- **RELAX** (ConstraintTarget): **MDL-deferred for v1.** Named constraints are predicates, not structure the
  code encodes, so RELAX has no honest structural delta yet (removing a constraint would spuriously look like
  free compression). `transport` returns the corpus unchanged for RELAX, so `mdl_delta == 0` → it does NOT
  clear the MDL gate and falls through to the existing qualitative bar (unchanged behavior). A constraint-aware
  code is documented future work.

---

## The gate + the novelty classifier

### `mdl_delta`
```
mdl_delta(claims, schema, revision) =
    L(transport(claims, schema, revision)) − L(claims, schema)      # < 0 == the revision pays for itself
```
computed over **object claims only** (exclude the revision claim and any other meta-claims).

### `novelty_residual` — the W&B pointwise residual, structural form
```
novelty_residual(claims, schema, revision) =
    Σ_{atom a in schema'  and  a NOT generator-reachable from schema} _structural_bits(a)
```
- **generator-reachable** = `a` is a rename or a merge-quotient of an existing schema atom (same structural
  signature, modulo MERGE) → residual 0.
- **composite-reachable / isolated** = `a` is a new combination / uses kinds absent from the old schema →
  residual = its structural description length.
- So a MERGE's unified pattern is generator-reachable → residual ≈ 0 (**consolidation**); an ADD/structure
  that introduces genuinely new composition → residual > 0 (**discovery**, if it also compresses).

### Gate-policy β (FLAGGED — W&B-faithful; one-liner to change)
The **gate is compression alone**; the residual **classifies**, it is not a second gate:
```
clears_mdl_bar(mdl_delta, *, eps_bits = _MDL_EPS) -> bool:
    return mdl_delta < -eps_bits          # strictly better by at least eps_bits (guards numerical noise)
```
`novelty_residual` is computed and recorded to **classify** a licensed revision and (future) to feed SELECT —
NOT to block licensing. The `(residual, mdl_delta)` plane:

| | `mdl_delta < −eps` (compresses) | `mdl_delta ≥ −eps` (doesn't) |
|---|---|---|
| **`residual ≈ 0`** | **consolidation** → license (`MDL_GATE`), tag *consolidation* | noise → hold/qualitative |
| **`residual > 0`** | **discovery** → license (`MDL_GATE`), tag *discovery* | speculative / schema-bloat → hold/qualitative |

This is W&B's retrieval/search/discovery trichotomy + a fourth cell (consolidation), all computed from the
corpus's own statistics. **If you'd rather require novelty to license** (reject pure consolidations), change
the gate to `residual >= _RESIDUAL_EPS and mdl_delta < -eps_bits` — a one-line edit; the rest is unaffected.

---

## Grammar surface (pure; over `Iterable[Claim]`; imports nothing from protocol — isolation holds)

New module `grammar/src/polymer_grammar/description_length.py`:
- `Schema` — a frozen ephemeral value `(patterns: frozenset[tuple[str,str]], terms: frozenset[str],
  constraints: frozenset[str])`. NOT stored on Corpus.
- `corpus_implied_schema(claims) -> Schema`
- `description_length(claims, schema) -> float`
- `transport(claims, schema, revision) -> tuple[tuple[Claim, ...], Schema]`
- `mdl_delta(claims, schema, revision) -> float`
- `novelty_residual(claims, schema, revision) -> float`
- `RevisionDiscovery` — a frozen record `(mdl_delta, novelty_residual, classification: Literal["discovery",
  "consolidation","rejected"])` for audit (protocol attaches it; see below).
- `clears_mdl_bar(mdl_delta, *, eps_bits=_MDL_EPS) -> bool`
- constants `_PATTERN_BITS`, `_FILL_BITS`, `_MDL_EPS` (tunable).

In `licensing.py`: add `LicenseRoute.MDL_GATE = "mdl_gate"`.

In `representation.py`: extend `meets_meta_tier_bar` to accept the MDL route:
```python
def meets_meta_tier_bar(licensing) -> bool:
    qualitative = (licensing.route == REPLICATION
                   and licensing.rival_set_closure in META_TIER_ALLOWED_CLOSURES)
    return qualitative or licensing.route == LicenseRoute.MDL_GATE
```
This is safe because of the security hardening already merged: `compile_untrusted` rejects any incoming
`licensing`, so an `MDL_GATE` route can ONLY be stamped by the trusted `verify_stage` after it actually
computes the delta. Nobody can forge it.

---

## Protocol wiring (`verify.py`, the representation-revision branch)

Today: a representation-revision in the LICENSED branch is held PENDING unless its auto-assembled
`Licensing(SEVERE_TEST, OPEN_ACKNOWLEDGED)` meets the (qualitative) bar — which it never does, so it always
holds. New: try the MDL route first.

```python
if is_representation_revision(c):
    object_claims = tuple(x for x in corpus.claims if not is_representation_revision(x))
    schema = corpus_implied_schema(object_claims)
    rev = c.representation_revision
    delta = mdl_delta(object_claims, schema, rev)
    if clears_mdl_bar(delta):
        residual = novelty_residual(object_claims, schema, rev)
        licensing = Licensing(route=LicenseRoute.MDL_GATE,
                              satisfactions=(ev.satisfaction,),        # the revision's own test passed
                              rival_set_closure=RivalSetClosure.ENUMERATED)
        # LICENSE c with this licensing; attach RevisionDiscovery(delta, residual, classify(residual)) to audit
    elif not meets_meta_tier_bar(licensing):     # licensing = the prior SEVERE_TEST block
        continue                                  # hold PENDING, exactly as today
```
- `meets_meta_tier_bar(MDL_GATE licensing)` is True, so the revision LICENSES on the compression evidence —
  no human replication required. This is the flywheel turning on schema: the REPRESENTATION RED-TEAM daemon
  proposes revisions and the MDL gate auto-adjudicates which are real.
- The `RevisionDiscovery` record (delta, residual, classification) rides on the verify `StageAudit` note (no
  Corpus-shape change). Full record-threading on `CycleResult` is a follow-up if richer audit is wanted.

---

## v1 scope / non-goals
- **In v1:** the code; `transport` for MERGE + ADD + DEPRECATE; `mdl_delta`; `novelty_residual`; `MDL_GATE`
  route; extended `meets_meta_tier_bar`; `verify_stage` wiring; classification tag in the audit.
- **Deferred:** RELAX through MDL (needs a constraint-aware code — routes to qualitative for now); SELECT
  using `novelty_residual` as a value axis (prioritize high-novelty revisions); field-resolved pattern
  signatures; full `RevisionDiscovery` threading on `CycleResult`; the categorical (copresheaf/Kan) formalism.
- **Invariants preserved:** pure/deterministic (no clock/random/IO); one-way isolation (grammar ↛ protocol);
  Corpus stays exactly 4 collections (`Schema` is ephemeral, derived); frozen-model discipline; the
  belief-neutrality of generation; the propose-but-never-license boundary.

## Acceptance
- Grammar: a redundant-MERGE corpus yields `mdl_delta < 0` and `novelty_residual ≈ 0` (consolidation); a
  load-bearing DEPRECATE yields `mdl_delta > 0` (rejected); an unused ADD yields `mdl_delta > 0`. Determinism:
  `description_length`/`mdl_delta` byte-stable across calls.
- Protocol: a representation-revision that compresses the object corpus LICENSES via `MDL_GATE` through
  `run_cycle` (counterfactual: with the revision NOT compressing, it stays PENDING). The meta-tier gate's
  prior behavior (hold non-compressing/SEVERE_TEST revisions) is unchanged. Belief-neutrality re-checked
  through `run_cycle`.
- Full grammar + protocol suites green; ruff clean; isolation holds; Corpus still 4 collections.
