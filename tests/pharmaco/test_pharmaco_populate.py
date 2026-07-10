"""Task 5: batch proposal + pre-registration. The pharmacogenomic engine is an untrusted proposer — propose_claims
turns mechanism-scan rows into claims (honest search_cardinality; NO drug is ever dropped — an
unknown-CHEBI drug falls back to the "other" ontology with a synthetic urn); preregister locks
e-LOND slots BEFORE any e-value exists."""
from __future__ import annotations

import pandas as pd
from polymer_grammar import FDRLedger
from polymer_protocol import Corpus

from polymer_claims.pharmaco_populate import preregister, propose_claims


def test_propose_sets_search_cardinality_and_never_drops_a_drug(caplog):
    res = pd.DataFrame([
        {"drug": "Palbociclib", "marker": "MTAP", "r_adj": -0.20, "level": "L3", "n_genes_tested": 8},
        {"drug": "MysteryDrug", "marker": "FOO", "r_adj": -0.15, "level": "L2", "n_genes_tested": 3},
    ])
    chebi = {"Palbociclib": "http://purl.obolibrary.org/obo/CHEBI_85993"}
    with caplog.at_level("INFO"):
        claims = propose_claims(res, ref="se:gdsc_pharmaco@1", chebi_of=chebi)
    assert len(claims) == 2                        # no drug dropped
    by_id = {c.id: c for c in claims}
    known = by_id["pgx-MTAP-Palbociclib"]
    assert known.provenance.search_cardinality == 8
    assert known.subject.parts[1].ontology == "CHEBI"

    unknown = by_id["pgx-FOO-MysteryDrug"]
    assert unknown.provenance.search_cardinality == 3
    assert unknown.subject.parts[1].ontology == "other"
    assert unknown.subject.parts[1].uri == "urn:pharmaco:drug:mysterydrug"
    assert "1" in caplog.text                       # fallback count logged, not silent


def test_preregister_locks_a_slot_before_any_evalue():
    res = pd.DataFrame([
        {"drug": "Palbociclib", "marker": "MTAP", "r_adj": -0.20, "level": "L3", "n_genes_tested": 8},
    ])
    chebi = {"Palbociclib": "http://purl.obolibrary.org/obo/CHEBI_85993"}
    claims = propose_claims(res, ref="se:gdsc_pharmaco@1", chebi_of=chebi)
    corpus = Corpus(fdr_ledger=FDRLedger(target_fdr=0.05))

    out = preregister(corpus, claims)

    assert claims[0].id in {c.id for c in out.claims}
    pending = [t for t in out.fdr_ledger.tests if t.claim_id == claims[0].id]
    assert len(pending) == 1
    assert pending[0].e_value is None                     # registered, unresolved
    assert pending[0].commitment_hash is not None          # pre-registration hash locked


def test_preregister_charges_in_strength_list_order_not_alphabetical():
    # List (strength-rank) order puts the STRONG signal first even though its claim id sorts
    # LAST alphabetically. e-LOND's front-loaded gamma_t weights must reach it at the earliest
    # (lowest-threshold) slot -> registration follows list order, NOT sorted(claim_ids).
    res = pd.DataFrame([
        {"drug": "Zoledronic", "marker": "MTAP", "level": "L3", "r_adj": -0.30, "n_genes_tested": 5},
        {"drug": "Aspirin", "marker": "AAA", "level": "L0", "r_adj": -0.05, "n_genes_tested": 5},
    ])
    claims = propose_claims(res, ref="se:gdsc_pharmaco@1", chebi_of={})
    assert [c.id for c in claims] == ["pgx-MTAP-Zoledronic", "pgx-AAA-Aspirin"]  # list = strength order

    out = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
    tests = out.fdr_ledger.tests

    # registration order == list order (strength), not alphabetical (which would put -AAA- first)
    assert [t.claim_id for t in tests] == ["pgx-MTAP-Zoledronic", "pgx-AAA-Aspirin"]
    assert [t.index for t in tests] == [1, 2]
    # the strong signal sits at position 1 -> the LARGEST alpha -> the LOWEST discovery bar
    strong, weak = tests[0], tests[1]
    assert strong.alpha_allocated > weak.alpha_allocated
    assert (1.0 / strong.alpha_allocated) < (1.0 / weak.alpha_allocated)
