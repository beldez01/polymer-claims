from __future__ import annotations

from polymer_grammar import FDRLedger
from polymer_grammar.fdr import FDRTest
from polymer_grammar.licensing import IndependenceTier

from polymer_claims._hashing import canonical_sha256
from polymer_claims.attestation import (
    _bare_hex,
    _digest_or_none,
    _external_parameters,
    _internal_parameters,
    _subject,
    distinct_cohort_reps,
)

from tests.attestation._fixtures import licensed_claim, licensing, mc, sat


def test_bare_hex_strips_algorithm_prefix():
    assert _bare_hex("sha256:abc123") == "abc123"
    assert _bare_hex("abc123") == "abc123"


def test_digest_or_none_accepts_valid_sha256_and_rejects_others():
    valid = "sha256:" + "a" * 64
    assert _digest_or_none(valid).sha256 == "a" * 64
    assert _digest_or_none("h1") is None
    assert _digest_or_none(None) is None
    assert _digest_or_none("sha256:tooshort") is None


def test_subject_digest_matches_canonical_claim_hash():
    claim = licensed_claim("c1", licensing(sat(mc())))
    expected = canonical_sha256(claim.model_dump(mode="json")).split(":", 1)[1]
    subj = _subject(claim)
    assert subj.name == "c1"
    assert subj.digest.sha256 == expected


def test_distinct_cohort_reps_dedups_and_sorts_by_dimnames_hash():
    s_b = sat(mc(dimnames_hash="sha256:bbb", mid="B"))
    s_a1 = sat(mc(dimnames_hash="sha256:aaa", mid="A1"))
    s_a2 = sat(mc(dimnames_hash="sha256:aaa", mid="A2"))  # duplicate cohort, dropped
    s_none = sat(mc(dimnames_hash=None, mid="N"))  # no cohort, dropped
    lic = licensing(s_b, s_a1, s_a2, s_none)
    reps = distinct_cohort_reps(lic)
    # ascending dimnames_hash, first occurrence: aaa(A1) then bbb(B)
    assert [s.materialization.id for s in reps] == ["A1", "B"]


def test_cohort_rep_parity_PRIVATE_GUARD():
    # Disposable drift alarm: delete if grammar's private `_distinct_cohort_reps` moves/renames.
    from polymer_grammar.licensing import _distinct_cohort_reps

    sats = (
        sat(mc(dimnames_hash="sha256:bbb", mid="B")),
        sat(mc(dimnames_hash="sha256:aaa", mid="A1")),
        sat(mc(dimnames_hash="sha256:aaa", mid="A2")),
        sat(mc(dimnames_hash=None, mid="N")),
    )
    lic = licensing(*sats)
    assert list(distinct_cohort_reps(lic)) == _distinct_cohort_reps(sats)


def test_external_parameters_pulls_fdr_ledger_fields():
    claim = licensed_claim("c1", licensing(sat(mc())))
    ledger = FDRLedger(
        target_fdr=0.05,
        tests=(FDRTest(index=3, claim_id="c1", e_value=42.0, alpha_allocated=0.0125, discovery=True),),
    )
    ep = _external_parameters(claim, claim.licensing, ledger)
    assert ep.claim_id == "c1"
    assert ep.pattern_id == "adjusted_effect"
    assert ep.license_route == "severe_test"
    assert ep.rival_set_closure == "enumerated"
    assert ep.target_fdr == 0.05
    assert ep.fdr_test_index == 3
    assert ep.fdr_alpha_allocated == 0.0125
    assert ep.fdr_e_value == 42.0


def test_external_parameters_without_matching_ledger_entry_omits_test_fields():
    claim = licensed_claim("c1", licensing(sat(mc())))
    ledger = FDRLedger(target_fdr=0.1)  # no tests
    ep = _external_parameters(claim, claim.licensing, ledger)
    assert ep.target_fdr == 0.1
    assert ep.fdr_test_index is None
    assert ep.fdr_alpha_allocated is None
    assert ep.fdr_e_value is None


def test_internal_parameters_reflects_tier_and_witness():
    lic = licensing(
        sat(mc(dimnames_hash="sha256:aaa", mid="M1")),
        sat(mc(dimnames_hash="sha256:bbb", mid="M2")),
        independence_tier=IndependenceTier.REPLICATED,
    )
    ip = _internal_parameters(lic, independence_witnessed=True)
    assert ip.independence_tier == "replicated"
    assert ip.independence_witnessed is True
    assert ip.severity_provenance is None
    assert ip.shared_cause_overlap is None
