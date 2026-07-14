"""residue.py — a read-only QUERY surface over the PENDING residue graveyard (residualism R2/R3).

The engine's residualism commitment (`foundations/residualism.md`) treats the PENDING set as a
FIRST-CLASS, queryable object — "structured residue retained for further inquiry", not deleted error
(R2) — and R3 says an iterating program progressively CONVERTS that residue into licensed claims. The
neg-whisper ③ work funded only the *scheduling weight* for re-exam (`economics.RESIDUE_REEXAM`); this
module adds the missing inspection/selection surface: it reads the graveyard's shape by pending-reason,
exposes each entry with the facets that decide re-conversion, and ranks the conversion candidates by
leverage.

It NEVER licenses. Actual conversion re-runs the EXISTING cycle (with better data, independent adapters,
or a fresh materialization); this surface only answers "what is left on the table, and what is worth
re-attempting". Pure: grammar + protocol DTOs only — no umbrella import, no numpy, no new Corpus
collection (read-only over the four that exist).
"""
from __future__ import annotations

from collections import Counter

from polymer_grammar import PendingReason, Status

from .base import _Model
from .corpus import Corpus

# Pending reasons that re-running the cycle ALONE cannot clear — each needs an external action (an
# ontology remap, a governance ruling, a definitional resolution) before a re-test is even meaningful.
# Every other reason is convertible in principle by more/better data, independent adapters, or a fresh
# materialization. Kept explicit + small so the classification is auditable, not a hidden heuristic.
_NEEDS_EXTERNAL_INPUT: frozenset[PendingReason] = frozenset(
    {
        PendingReason.ONTOLOGY_TERM_OBSOLETE,
        PendingReason.DEFINITIONAL_COMMITMENT_CONTESTED,
        PendingReason.UNREPRODUCIBLE_BY_GOVERNANCE,
    }
)


def reason_needs_external_input(reason: PendingReason | None) -> bool:
    """True iff clearing this pending-reason requires an external action (remap/governance/definition),
    so re-running the cycle alone won't convert it. None (no reason recorded) counts as convertible."""
    return reason in _NEEDS_EXTERNAL_INPUT


class ResidueEntry(_Model):
    """A read-only view of one PENDING claim in the graveyard, carrying the facets that decide whether —
    and how urgently — its residue can be converted back into a licensed claim."""

    claim_id: str
    title: str
    pending_reason: PendingReason | None = None
    testable: bool  # has an evaluation_plan → can be dispatched to the cycle at all
    needs_external_input: bool  # blocked on an external action; a re-run alone won't help
    dependents: int  # incident defeat edges (source or target) — its connectivity/blast radius


def _dependents_map(corpus: Corpus) -> Counter:
    """For each claim id, the number of defeat edges it touches (as source OR target). A coarse leverage
    proxy: converting a highly-connected PENDING claim moves the most downstream inquiry — the query-side
    echo of ③'s dependency-degree residue-value."""
    counts: Counter = Counter()
    for e in corpus.defeat_edges:
        counts[e.source] += 1
        counts[e.target] += 1
    return counts


def residue_census(corpus: Corpus) -> dict[PendingReason | None, int]:
    """The SHAPE of the graveyard: how many PENDING claims carry each pending-reason (None bucketed on
    its own key). LICENSED/REJECTED/CONJECTURED claims are not residue and never appear."""
    return dict(Counter(c.pending_reason for c in corpus.claims if c.status == Status.PENDING))


def residue_graveyard(corpus: Corpus) -> tuple[ResidueEntry, ...]:
    """Every PENDING claim as a ResidueEntry, ordered by claim id. The first-class, inspectable residue
    set (R2): structured and retained, not deleted error."""
    deps = _dependents_map(corpus)
    entries = [
        ResidueEntry(
            claim_id=c.id,
            title=c.title,
            pending_reason=c.pending_reason,
            testable=c.evaluation_plan is not None,
            needs_external_input=reason_needs_external_input(c.pending_reason),
            dependents=deps.get(c.id, 0),
        )
        for c in corpus.claims
        if c.status == Status.PENDING
    ]
    return tuple(sorted(entries, key=lambda e: e.claim_id))


def query_residue(
    corpus: Corpus,
    *,
    reason: PendingReason | None = None,
    testable: bool | None = None,
    needs_external_input: bool | None = None,
) -> tuple[ResidueEntry, ...]:
    """Filter the graveyard by any combination of facets. A None facet does not filter (so the default
    call returns the whole graveyard); note this means you cannot filter *for* a None pending_reason."""
    out = residue_graveyard(corpus)
    if reason is not None:
        out = tuple(e for e in out if e.pending_reason == reason)
    if testable is not None:
        out = tuple(e for e in out if e.testable == testable)
    if needs_external_input is not None:
        out = tuple(e for e in out if e.needs_external_input == needs_external_input)
    return out


def conversion_candidates(corpus: Corpus) -> tuple[ResidueEntry, ...]:
    """The R3 re-conversion worklist: PENDING claims a cycle re-run could actually convert — testable
    (has a plan) AND not blocked on external input — ranked by leverage (dependents desc, then id). This
    only SURFACES what to re-attempt; conversion itself re-runs the existing cycle."""
    cand = [e for e in residue_graveyard(corpus) if e.testable and not e.needs_external_input]
    return tuple(sorted(cand, key=lambda e: (-e.dependents, e.claim_id)))
