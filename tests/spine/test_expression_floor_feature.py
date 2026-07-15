"""Ch1b viral lane — a non-human feature (viral transcript) gets a legal subject and licenses.

The blocker: expression_floor_claim hard-codes an HGNC GeneOrProtein subject, which a viral feature
(LMP1) cannot satisfy (the grammar requires hgnc|ensembl_gene|uniprot). expression_floor_feature_claim
takes an explicit subject (a GenomicRegion on the EBV contig) + a feature row key, and the sibling
expression::floor_feature cell (subject kind=None) accepts it. Reuses the mean/HL adapter engine.
"""
from __future__ import annotations

import pytest
from polymer_grammar import (
    FDRLedger,
    GeneOrProtein,
    GeneOrProteinIdentifiers,
    GenomicRegion,
    MaterializationContext,
    Status,
)
from polymer_protocol import Corpus, run_cycle

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract

_EBV = GenomicRegion(id="ebv:LMP1", display="EBV LMP1 transcript", assembly="EBV(NC_007605)",
                     chrom="NC_007605.1", start=169474, end=170949, strand="+")


def _viral_contract(tmp_path):
    # LMP1 over-expressed in EBV+ (level_a), absent in EBV- (level_b). 12 pos replicates so the
    # betting e-value clears the e-LOND first-test bar (mirrors the floor license fixture).
    pos = {f"p{i}": 95.0 + i for i in range(12)}
    neg = {f"n{i}": 0.01 * i for i in range(40)}
    grp = {**{k: "EBV_pos" for k in pos}, **{k: "EBV_neg" for k in neg}}
    tpm = {"LMP1": {**pos, **neg}}
    build_fusion_expr_contract(tpm, grp, {k: "" for k in grp}, genes=["LMP1"], out_dir=tmp_path)
    _c.clear_contract_cache()
    return "se:tcga_laml_fusion_expr@1"


def test_hgnc_builder_cannot_carry_a_viral_feature():
    # Documents the blocker: a viral feature has no HGNC id, so the GeneOrProtein subject is illegal.
    with pytest.raises(ValueError):
        GeneOrProtein(id="HGNC:LMP1", display="LMP1", entity_type="gene",
                      identifiers=GeneOrProteinIdentifiers(symbol="LMP1"))  # no hgnc/ensembl/uniprot


def test_feature_claim_constructs_with_a_genomic_region_subject():
    from polymer_claims.expression_floor_adapters import expression_floor_feature_claim
    claim = expression_floor_feature_claim(
        "floor-LMP1", ref="se:x@1", feature="LMP1", subject=_EBV, floor=13.0, tissue="EBV+ lymphoma",
        level_a="EBV_pos", level_b="EBV_neg", search_cardinality=1)
    assert claim.subject.kind == "genomic_region"
    assert claim.subject.assembly == "EBV(NC_007605)"


def test_viral_over_expression_licenses_via_the_feature_cell(tmp_path):
    from polymer_claims.capabilities import CAPABILITY_CELLS
    from polymer_claims.expression_floor_adapters import (
        ExpressionFloorHLAdapter, ExpressionFloorMeanAdapter, expression_floor_feature_claim,
        expression_floor_feature_oracle_registry, expression_floor_registry,
    )
    from polymer_claims.expression_floor_evidence import expression_floor_evalue
    from polymer_claims.expression_floor_populate import preregister
    from polymer_claims.evidence import _terminal_node

    ref = _viral_contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        claim = expression_floor_feature_claim(
            "floor-LMP1", ref=ref, feature="LMP1", subject=_EBV, floor=13.0, tissue="EBV+ lymphoma",
            level_a="EBV_pos", level_b="EBV_neg", search_cardinality=1)
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), [claim])
        ev = expression_floor_evalue(_terminal_node(claim))
        ctx = MaterializationContext(id="M", api_version="v1", data_version="d1")
        out = run_cycle(
            corpus, (ExpressionFloorMeanAdapter(), ExpressionFloorHLAdapter()), ctx,
            adapter_registry=expression_floor_registry(),
            oracles=expression_floor_feature_oracle_registry(),
            evidence={"floor-LMP1": ev},
            capability_registry=CAPABILITY_CELLS)
    assert out.corpus.by_id()["floor-LMP1"].status is Status.LICENSED
