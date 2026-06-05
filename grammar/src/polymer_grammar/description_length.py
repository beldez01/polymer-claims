"""Two-part structural description-length code over the typed claim corpus (MDL meta-tier).

`L(claims, schema) = L_schema(schema) + L_corpus(claims, schema)` — a pure, deterministic,
structural / representational MDL code (NOT predictive-model compression of raw data; NOT
copresheaves/Kan extensions). It scores *representational parsimony*: does this schema express
the corpus of claims compactly. The schema is an explicit, ephemeral, derived value (NOT a 5th
Corpus collection), so ADD/DEPRECATE of a declared-but-unused atom is priced correctly.

Locked choices (see spec 2026-06-05-mdl-meta-tier-design.md):
  1. structural granularity — encode the skeleton only (which pattern, which selectors); raw
     quantity values are a fixed per-slot cost (`_FILL_BITS`) that cancels in every `mdl_delta`.
  2. corpus-relative ontology cost — every selector priced by empirical frequency `-log2(freq)`.
  3. `log*` (Rissanen universal integer code) for schema-size counts (honest prefix-code bits).

Pure/deterministic: frequencies from the frozen claim list; `log2`/`log*` only; NO clock/random/IO.
Imports nothing from polymer_protocol (one-way isolation holds).
"""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable
from typing import Literal

from pydantic import Field

from .base import _Model
from .claim import Claim
from .leaf import CategoricalLeaf, PropositionLeaf, QuantityLeaf
from .pattern import PatternRef
from .representation import (
    OntologyTermTarget,
    PatternTarget,
    RepresentationRevision,
    RevisionOperation,
)

# --- tunable constants (module-level, documented) --------------------------------------------
_PATTERN_BITS = 8.0   # flat per-pattern schema-table cost; a MERGE's saving is exactly this/pattern
_FILL_BITS = 4.0      # fixed per-structural-slot fill cost; cancels in mdl_delta
_MDL_EPS = 1.0        # the gate's compression margin (bits) — guards numerical noise
# Inflated fill for claims repointed to the synthetic generic pattern by a DEPRECATE transport;
# strictly > _FILL_BITS so deprecating a load-bearing specific pattern RAISES the corpus code.
_GENERIC_FILL_BITS = 32.0
# The synthetic generic pattern id a DEPRECATE transport repoints dependent claims onto. It is
# NOT a real schema atom; it is priced via _GENERIC_FILL_BITS in _corpus_code_length.
_GENERIC_PATTERN_ID = "__generic__"
# Inflated per-selector cost for the synthetic generic TERM a term-DEPRECATE repoints in-use term
# selectors onto. Strictly large (a full new-pattern's worth of bits) so re-encoding a still-in-use
# term RAISES total cost -> deprecating a load-bearing term is rejected. Keeps the two-part code
# coherent: no claim emits a term that the post-transport schema fails to declare (the sentinel is
# priced internally here, never as a frequency selector against schema.terms).
_GENERIC_TERM_BITS = 32.0
# The synthetic generic term id a term-DEPRECATE repoints dependent term selectors onto. NOT a real
# schema atom; priced via _GENERIC_TERM_BITS in _corpus_code_length.
_GENERIC_TERM_ID = "__generic_term__"

_LOG_STAR_CONST = math.log2(2.865)


class Schema(_Model):
    """An ephemeral, derived value: the structural skeleton implied by a claim corpus.

    `patterns` keyed by (PatternRef.id, version); `terms` = distinct categorical ontology terms +
    ontology_term-kind subject ids; `constraints` = frozenset() for v1 (no constraint source yet).
    NOT stored on Corpus — `corpus_implied_schema` recomputes it on demand.
    """

    patterns: frozenset[tuple[str, str]] = Field(default_factory=frozenset)
    terms: frozenset[str] = Field(default_factory=frozenset)
    constraints: frozenset[str] = Field(default_factory=frozenset)


def _pattern_key(claim: Claim) -> tuple[str, str]:
    return (claim.pattern.id, claim.pattern.version)


def _claim_terms(claim: Claim) -> tuple[str, ...]:
    """The ontology-term selector slots of a claim: every CategoricalLeaf.ontology_term plus an
    ontology_term-kind subject id (if present). Order-stable for determinism."""
    terms: list[str] = []
    for leaf in claim.leaves:
        if isinstance(leaf, CategoricalLeaf):
            terms.append(leaf.ontology_term)
    subj = claim.subject
    if subj is not None and getattr(subj, "kind", None) == "ontology_term":
        terms.append(subj.id)
    return tuple(terms)


def _n_structural_slots(claim: Claim) -> int:
    """A deterministic count of the claim's quantity/proposition structural slots — the leaves
    that carry a fixed-cost fill (QuantityLeaf values, PropositionLeaf warrants). Pure count."""
    return sum(
        1 for leaf in claim.leaves if isinstance(leaf, (QuantityLeaf, PropositionLeaf))
    )


def corpus_implied_schema(claims: Iterable[Claim]) -> Schema:
    """Derive the structural schema a claim corpus commits to (pure; order-independent)."""
    claims = tuple(claims)
    patterns = frozenset(_pattern_key(c) for c in claims)
    terms: set[str] = set()
    for c in claims:
        terms.update(_claim_terms(c))
    return Schema(patterns=patterns, terms=frozenset(terms), constraints=frozenset())


def _log_star(n: int) -> float:
    """Rissanen's universal code for a positive integer: log2(2.865) + log2(n) + log2(log2 n) + …
    summing only the positive iterated-log terms. For n <= 1 return the constant alone."""
    if n <= 1:
        return _LOG_STAR_CONST
    total = _LOG_STAR_CONST
    value = math.log2(n)
    while value > 0.0:
        total += value
        value = math.log2(value)
    return total


def _schema_cost(schema: Schema) -> float:
    """L_schema = log*(K) + K*_PATTERN_BITS + log*(T) + log*(C)."""
    k = len(schema.patterns)
    t = len(schema.terms)
    c = len(schema.constraints)
    return _log_star(k) + k * _PATTERN_BITS + _log_star(t) + _log_star(c)


def _corpus_code_length(claims: Iterable[Claim], schema: Schema) -> float:
    """L_corpus = Σ_claim [ -log2(freq_pattern) + Σ_selector -log2(freq_term) + fill*slots ].

    Frequencies are corpus-relative empirical counts (pure). The pattern-selector total is
    N·H(pattern distribution) — the term a MERGE compresses. Claims repointed to the synthetic
    `__generic__` pattern (by a DEPRECATE transport) are priced with the inflated
    `_GENERIC_FILL_BITS` so deprecating a load-bearing specific pattern RAISES the cost.
    Guards: empty corpus -> 0.0; never log2(0)."""
    claims = tuple(claims)
    n = len(claims)
    if n == 0:
        return 0.0

    pattern_counts = Counter(_pattern_key(c) for c in claims)
    term_counts: Counter[str] = Counter()
    total_term_slots = 0
    for c in claims:
        for term in _claim_terms(c):
            if term == _GENERIC_TERM_ID:
                continue  # sentinel is priced at a flat inflated cost, not a frequency
            term_counts[term] += 1
            total_term_slots += 1

    total = 0.0
    for c in claims:
        # pattern selector, frequency-weighted
        count = pattern_counts[_pattern_key(c)]
        total += -math.log2(count / n)
        # term selectors, corpus-relative frequency (sentinel priced at the inflated flat cost)
        for term in _claim_terms(c):
            if term == _GENERIC_TERM_ID:
                total += _GENERIC_TERM_BITS
            else:
                total += -math.log2(term_counts[term] / total_term_slots)
        # fixed per-slot fill (inflated for generic-pointed claims)
        fill = _GENERIC_FILL_BITS if c.pattern.id == _GENERIC_PATTERN_ID else _FILL_BITS
        total += fill * _n_structural_slots(c)
    return total


def description_length(claims: Iterable[Claim], schema: Schema) -> float:
    """L(claims, schema) = L_schema(schema) + L_corpus(claims, schema). Pure + deterministic.

    Guard: an empty corpus has zero description length (nothing to encode)."""
    claims = tuple(claims)
    if not claims:
        return 0.0
    return _schema_cost(schema) + _corpus_code_length(claims, schema)


# --- transport: the structural rewrite (Left-Kan analog), per operation -----------------------

def _merged_ref(member_ids: Iterable[str]) -> PatternRef:
    """Deterministic unified ref id for a MERGE: sorted member ids joined under a `merged:` head."""
    joined = "+".join(sorted(member_ids))
    return PatternRef(id="merged:" + joined, version="v1")


def _revalidate(claim: Claim, new_pattern: PatternRef) -> Claim:
    """Repoint a claim's pattern, re-running validators (model_copy bypasses them)."""
    return Claim.model_validate(
        claim.model_copy(update={"pattern": new_pattern}).model_dump()
    )


def _repoint_term(claim: Claim, target_term: str) -> Claim:
    """Repoint every CategoricalLeaf.ontology_term (and an ontology_term subject id) that equals
    `target_term` to the synthetic `_GENERIC_TERM_ID` sentinel, re-running validators. Used by a
    term-DEPRECATE so a deprecated term leaves no dangling selector (code stays coherent) and a
    still-in-use term re-encodes at the inflated `_GENERIC_TERM_BITS` (so DEPRECATE is rejected)."""
    if target_term not in _claim_terms(claim):
        return claim  # nothing to repoint
    data = claim.model_dump()
    for leaf in data["leaves"]:
        if leaf.get("kind") == "categorical" and leaf.get("ontology_term") == target_term:
            leaf["ontology_term"] = _GENERIC_TERM_ID
    subj = data.get("subject")
    if subj is not None and subj.get("kind") == "ontology_term" and subj.get("id") == target_term:
        subj["id"] = _GENERIC_TERM_ID
    return Claim.model_validate(data)


def transport(
    claims: Iterable[Claim], schema: Schema, revision: RepresentationRevision
) -> tuple[tuple[Claim, ...], Schema]:
    """Deterministically rewrite (claims, schema) under a revision (pure; the Left-Kan analog).

    MERGE     — unify the >=2 member patterns into one `merged:` ref; repoint every claim on a
                member to the unified ref; schema' = members removed + unified added.
    ADD       — claims unchanged; schema' gains the declared pattern/term atom.
    DEPRECATE — schema' drops the target atom. For a pattern target, claims on it are repointed to
                the synthetic generic `__generic__` ref; for an ontology-term target, in-use term
                selectors are repointed to the `__generic_term__` sentinel. Both sentinels are NOT
                schema atoms — priced via `_GENERIC_FILL_BITS` / `_GENERIC_TERM_BITS` in
                `_corpus_code_length`, so deprecating a load-bearing pattern OR term RAISES the
                corpus code (rejected), while the code stays coherent (no dangling selector).
    RELAX     — MDL-deferred: returns (claims, schema) unchanged -> mdl_delta == 0.
    """
    claims = tuple(claims)
    op = revision.operation
    target = revision.target

    if op == RevisionOperation.MERGE:
        assert isinstance(target, PatternTarget)
        members = {(p.id, p.version) for p in target.patterns}
        unified = _merged_ref(p.id for p in target.patterns)
        new_claims = tuple(
            _revalidate(c, unified) if _pattern_key(c) in members else c for c in claims
        )
        new_patterns = (schema.patterns - members) | {(unified.id, unified.version)}
        return new_claims, schema.model_copy(update={"patterns": new_patterns})

    if op == RevisionOperation.ADD:
        if isinstance(target, PatternTarget):
            (ref,) = target.patterns
            new_patterns = schema.patterns | {(ref.id, ref.version)}
            return claims, schema.model_copy(update={"patterns": new_patterns})
        assert isinstance(target, OntologyTermTarget)
        new_terms = schema.terms | {target.term_id}
        return claims, schema.model_copy(update={"terms": new_terms})

    if op == RevisionOperation.DEPRECATE:
        if isinstance(target, PatternTarget):
            (ref,) = target.patterns
            key = (ref.id, ref.version)
            generic = PatternRef(id=_GENERIC_PATTERN_ID, version="v1")
            new_claims = tuple(
                _revalidate(c, generic) if _pattern_key(c) == key else c for c in claims
            )
            new_patterns = schema.patterns - {key}
            return new_claims, schema.model_copy(update={"patterns": new_patterns})
        assert isinstance(target, OntologyTermTarget)
        # Symmetric with pattern-DEPRECATE: repoint every in-use selector to the generic-term
        # sentinel (priced via _GENERIC_TERM_BITS) so the deprecated term leaves no dangling
        # selector and a load-bearing term re-encodes at a HIGHER cost (rejected). An unused term
        # repoints nothing -> only the log*(T) schema saving applies.
        new_claims = tuple(_repoint_term(c, target.term_id) for c in claims)
        new_terms = schema.terms - {target.term_id}
        return new_claims, schema.model_copy(update={"terms": new_terms})

    # RELAX (ConstraintTarget): MDL-deferred — no honest structural delta yet.
    return claims, schema


# --- the gate + the novelty classifier --------------------------------------------------------

def mdl_delta(
    claims: Iterable[Claim], schema: Schema, revision: RepresentationRevision
) -> float:
    """L(transport(...)) - L(claims, schema). < 0 == the revision pays for itself. Computed over
    object claims only (the caller excludes meta-claims). Pure + deterministic."""
    claims = tuple(claims)
    new_claims, new_schema = transport(claims, schema, revision)
    return description_length(new_claims, new_schema) - description_length(claims, schema)


def _generator_reachable(atom: tuple[str, str], schema: Schema) -> bool:
    """True iff a schema'-pattern atom is generator-reachable from the prior `schema` — i.e. it is
    a rename or MERGE-quotient of an existing atom (so it introduces NO new structure).

    Reachability test (explicit + documented): an already-present atom is trivially reachable; a
    `merged:`-prefixed atom is a genuine MERGE quotient ONLY when it carries real merge provenance —
    i.e. its `<id>+<id>+…` members are ALL pattern ids present in the prior schema (this is exactly
    the id `_merged_ref` mints from existing members). This avoids the prior raw string-prefix
    heuristic: a brand-new ADD of a pattern literally named `merged:foo` whose `foo` is NOT a prior
    member is correctly NOT reachable (residual > 0). Any other brand-new id is not derivable -> not
    reachable (a genuine ADD of new structure).
    """
    if atom in schema.patterns:
        return True
    atom_id, _ = atom
    if atom_id.startswith("merged:"):
        members = atom_id[len("merged:"):].split("+")
        prior_ids = {pid for (pid, _ver) in schema.patterns}
        # a real quotient names >=2 prior members, all of which existed before the merge.
        return len(members) >= 2 and all(m in prior_ids for m in members)
    return False


def novelty_residual(
    claims: Iterable[Claim], schema: Schema, revision: RepresentationRevision
) -> float:
    """The W&B pointwise residual (structural form): sum `_PATTERN_BITS` over schema' pattern atoms
    NOT generator-reachable from the prior schema. A MERGE's unified pattern is a quotient ->
    residual 0 (consolidation); a brand-new ADD pattern is not derivable -> residual `_PATTERN_BITS`
    (discovery, if it also compresses)."""
    claims = tuple(claims)
    _, new_schema = transport(claims, schema, revision)
    return sum(
        _PATTERN_BITS
        for atom in new_schema.patterns
        if not _generator_reachable(atom, schema)
    )


def clears_mdl_bar(mdl_delta_value: float, *, eps_bits: float = _MDL_EPS) -> bool:
    """The MDL gate: True iff the revision compresses by at least `eps_bits` (guards numeric noise).
    Compression alone is the gate; the residual classifies, it does not block (gate-policy beta)."""
    return mdl_delta_value < -eps_bits


def classify(
    mdl_delta_value: float, residual: float, *, eps_bits: float = _MDL_EPS
) -> Literal["discovery", "consolidation", "rejected"]:
    """The (residual, mdl_delta) plane: compresses + novel -> discovery; compresses + not-novel ->
    consolidation; otherwise rejected."""
    if not clears_mdl_bar(mdl_delta_value, eps_bits=eps_bits):
        return "rejected"
    return "discovery" if residual > 0.0 else "consolidation"


class RevisionDiscovery(_Model):
    """A frozen audit record of an adjudicated representation revision (protocol attaches it)."""

    mdl_delta: float
    novelty_residual: float
    classification: Literal["discovery", "consolidation", "rejected"]
