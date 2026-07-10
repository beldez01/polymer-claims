"""Task 5: batch proposal + pre-registration. STRATA is an untrusted proposer — propose_claims
turns mechanism-scan rows into claims (honest search_cardinality, skip unknown-CHEBI drugs);
preregister locks e-LOND slots BEFORE any e-value exists."""
from __future__ import annotations

import pandas as pd
from polymer_grammar import FDRLedger
from polymer_protocol import Corpus

from polymer_claims.strata_populate import preregister, propose_claims


def test_propose_sets_search_cardinality_and_skips_unknown_chebi(caplog):
    res = pd.DataFrame([
        {"drug": "Palbociclib", "marker": "MTAP", "r_adj": -0.20, "level": "L3", "n_genes_tested": 8},
        {"drug": "MysteryDrug", "marker": "FOO", "r_adj": -0.15, "level": "L2", "n_genes_tested": 3},
    ])
    chebi = {"Palbociclib": "http://purl.obolibrary.org/obo/CHEBI_85993"}
    with caplog.at_level("WARNING"):
        claims = propose_claims(res, ref="se:gdsc_pharmaco@1", chebi_of=chebi)
    assert len(claims) == 1                       # MysteryDrug skipped (no CHEBI)
    assert claims[0].provenance.search_cardinality == 8
    assert "1" in caplog.text                      # skipped count logged, not silent


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
