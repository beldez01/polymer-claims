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

from pydantic import Field

from .base import _Model
from .claim import Claim
from .leaf import CategoricalLeaf, PropositionLeaf, QuantityLeaf

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
            term_counts[term] += 1
            total_term_slots += 1

    total = 0.0
    for c in claims:
        # pattern selector, frequency-weighted
        count = pattern_counts[_pattern_key(c)]
        total += -math.log2(count / n)
        # term selectors, corpus-relative frequency
        for term in _claim_terms(c):
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
