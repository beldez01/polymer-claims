"""Task 5: batch proposal + pre-registration. STRATA is an untrusted proposer — propose_claims
turns mechanism-scan rows into claims (honest search_cardinality; NO drug is ever dropped — an
unknown-CHEBI drug falls back to the "other" ontology with a synthetic urn); preregister locks
e-LOND slots BEFORE any e-value exists."""
from __future__ import annotations

import pandas as pd
from polymer_grammar import FDRLedger
from polymer_protocol import Corpus

from polymer_claims.strata_populate import preregister, propose_claims


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
    assert unknown.subject.parts[1].uri == "urn:strata:drug:mysterydrug"
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
