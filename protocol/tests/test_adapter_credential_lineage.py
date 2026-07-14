"""R1 — provenance-lineage on AdapterCredential; a shared lineage tag defeats independence.

Additive field (default ()); the strengthened `adapters_independent` is byte-identical for any
registry without lineage (covered too by the unchanged existing adapter-registry suite).
"""
from __future__ import annotations

from polymer_protocol import AdapterCredential, adapters_independent


def _cred(identity, owner, ihash, *, lineage=()):
    return AdapterCredential(
        identity=identity, owner=owner, implementation_hash=ihash, lineage=lineage
    )


def test_lineage_defaults_empty():
    c = _cred("a", "o", "h")
    assert c.lineage == ()


def test_no_lineage_behaves_as_before():
    # different owner + hash, no lineage -> independent (pre-R1 behavior preserved)
    assert adapters_independent(_cred("a", "o1", "h1"), _cred("b", "o2", "h2"))
    # same owner -> not independent (unchanged)
    assert not adapters_independent(_cred("a", "o", "h1"), _cred("b", "o", "h2"))


def test_shared_lineage_defeats_independence():
    # DIFFERENT owner + DIFFERENT hash, but a SHARED lineage tag -> NOT independent
    a = _cred("am", "deepmind", "h1", lineage=("org:deepmind", "trained_on:clinvar"))
    b = _cred("esm", "meta", "h2", lineage=("org:meta", "trained_on:clinvar"))
    assert not adapters_independent(a, b)


def test_disjoint_lineage_stays_independent():
    a = _cred("am", "deepmind", "h1", lineage=("org:deepmind", "trained_on:uniprot"))
    b = _cred("esm", "meta", "h2", lineage=("org:meta", "trained_on:clinvar"))
    assert adapters_independent(a, b)


def test_shared_lineage_still_blocked_when_untrusted_or_same_owner():
    # the quad is conjunctive — shared lineage doesn't rescue any other failing condition
    a = _cred("am", "o", "h1", lineage=("x",))
    b = _cred("esm", "o", "h2", lineage=("y",))  # same owner
    assert not adapters_independent(a, b)
