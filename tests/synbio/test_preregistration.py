"""Durendal pre-registration mechanics (synbio Phase 3) — commit-before-data sealing.

Machinery only, on SYNTHETIC seed claims: deterministic commitment_hash, α-slot charged, firewall
exclusions kept out of the seal. Does NOT curate a real seed or run the Durendal derivation.
"""
from __future__ import annotations

from polymer_grammar import FDRLedger

from polymer_claims.synbio.firewall import assemble_blinded_seed
from polymer_claims.synbio.preregistration import seal_preregistration

# synthetic candidates: two admissible (upstream) + one conclusion-leak (excluded by the firewall)
_CANDIDATES = [
    ("c-affinity", "the affinity–discrimination law", "2015-01-01"),
    ("c-floor", "expression floors gate the effector", "2016-01-01"),
    ("c-answer", "topology-rejection of RUNX1T1 WT off-targets", "2010-01-01"),  # leaks -> excluded
]
_PLAN = {"id": "durendal-v1", "steps": ["walk-fusion-catalog", "instantiate-sense-and-kill"]}


def test_seal_is_deterministic_and_charges_an_alpha_slot():
    seed = assemble_blinded_seed(_CANDIDATES, cutoff_date="2020-01-01")
    ledger = FDRLedger(target_fdr=0.05)

    rec, led2 = seal_preregistration(seed, _PLAN, ledger=ledger, derivation_id="durendal")
    # only the two admissible priors are in the seal; the leaking candidate is excluded
    assert rec.seed_claim_ids == ("c-affinity", "c-floor")
    assert rec.n_excluded == 1
    # α-slot charged (commit-before-data): one pending test appended, carrying the commitment hash
    assert led2.n_tests == ledger.n_tests + 1
    slot = led2.tests[-1]
    assert slot.claim_id == "durendal" and slot.e_value is None
    assert slot.commitment_hash == rec.commitment_hash
    assert rec.alpha_allocated == slot.alpha_allocated and rec.fdr_test_index == slot.index

    # SAME seed + plan -> SAME commitment (deterministic)
    rec_again, _ = seal_preregistration(seed, _PLAN, ledger=FDRLedger(target_fdr=0.05), derivation_id="durendal")
    assert rec_again.commitment_hash == rec.commitment_hash


def test_different_plan_or_seed_changes_the_commitment():
    seed = assemble_blinded_seed(_CANDIDATES, cutoff_date="2020-01-01")
    base, _ = seal_preregistration(seed, _PLAN, ledger=FDRLedger(target_fdr=0.05), derivation_id="d")

    other_plan, _ = seal_preregistration(
        seed, {"id": "durendal-v2", "steps": []}, ledger=FDRLedger(target_fdr=0.05), derivation_id="d"
    )
    assert other_plan.commitment_hash != base.commitment_hash

    smaller_seed = assemble_blinded_seed(_CANDIDATES[:1], cutoff_date="2020-01-01")
    other_seed, _ = seal_preregistration(
        smaller_seed, _PLAN, ledger=FDRLedger(target_fdr=0.05), derivation_id="d"
    )
    assert other_seed.commitment_hash != base.commitment_hash


def test_a_conclusion_leaking_candidate_is_never_in_the_seal():
    seed = assemble_blinded_seed(_CANDIDATES, cutoff_date="2020-01-01")
    rec, _ = seal_preregistration(seed, _PLAN, ledger=FDRLedger(target_fdr=0.05), derivation_id="d")
    assert "c-answer" not in rec.seed_claim_ids
    assert "c-answer" not in rec.admissibility
