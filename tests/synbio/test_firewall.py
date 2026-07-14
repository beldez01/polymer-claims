"""synbio Phase 3 — the pre-registration firewall (process-enforced conceptual-leakage guard).

Conclusion-stripping (an answer-leaking claim is inadmissible even if old) + optional date-cutoff,
each admitted claim tagged with the deciding rule. Additive harness; NOT the licensing gate. The
operator's independent no-leakage review + the Durendal pre-registration remain out of scope.
"""
from __future__ import annotations

from polymer_claims.synbio.firewall import (
    Admissibility,
    assemble_blinded_seed,
    check_admissibility,
)


def test_upstream_claim_is_admissible():
    r = check_admissibility("the affinity–discrimination law bounds ON/OFF selectivity")
    assert r.admissible
    assert "upstream" in r.rule


def test_conclusion_leak_is_inadmissible():
    r = check_admissibility("RUNX1-RUNX1T1+ AML is killed by a direct-caspase effector")
    assert r.verdict is Admissibility.INADMISSIBLE_CONCLUSION_LEAK
    assert "runx1-runx1t1" in r.leaked_tokens and "direct-caspase" in r.leaked_tokens


def test_conclusion_stripping_wins_over_an_old_date():
    # an answer-leaking claim is OUT even if it pre-dates the cutoff (both mechanisms, §4)
    r = check_admissibility(
        "opto-CAR genotype-directed cytotoxicity", source_date="1990-01-01", cutoff_date="2020-01-01"
    )
    assert r.verdict is Admissibility.INADMISSIBLE_CONCLUSION_LEAK


def test_date_cutoff_excludes_post_insight_sources():
    # clean text, but the source post-dates the insight cutoff
    r = check_admissibility(
        "a general recognition-thermodynamics constraint", source_date="2024-06-01", cutoff_date="2020-01-01"
    )
    assert r.verdict is Admissibility.INADMISSIBLE_POST_CUTOFF


def test_clean_pre_cutoff_source_is_admissible():
    r = check_admissibility(
        "expression floors gate effector activation", source_date="2018-01-01", cutoff_date="2020-01-01"
    )
    assert r.admissible


def test_assemble_blinded_seed_partitions_and_tags():
    candidates = [
        ("c-affinity", "the affinity–discrimination law", "2015-01-01"),
        ("c-floor", "expression floors gate the effector", "2016-01-01"),
        ("c-answer", "topology-rejection of RUNX1T1 WT off-targets", "2010-01-01"),  # leaks
        ("c-late", "a clean but post-insight technique", "2025-01-01"),               # post-cutoff
    ]
    seed = assemble_blinded_seed(candidates, cutoff_date="2020-01-01")
    assert set(seed.admitted) == {"c-affinity", "c-floor"}
    assert set(seed.rejected) == {"c-answer", "c-late"}
    assert seed.rejected["c-answer"].verdict is Admissibility.INADMISSIBLE_CONCLUSION_LEAK
    assert seed.rejected["c-late"].verdict is Admissibility.INADMISSIBLE_POST_CUTOFF
    assert seed.n_conclusion_leaks_caught == 1
    # every admitted claim carries a deciding-rule tag (the admissibility record)
    assert all(tag for tag in seed.admitted.values())
