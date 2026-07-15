"""Audit F2 — a data-channel capability (requires_evidence=True) cannot license via the no-e-value
3-way route. The same claim licenses WITH an e-value and is withheld WITHOUT one.
"""
from __future__ import annotations

from polymer_grammar import FDRLedger, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims import contracts as _c
from polymer_claims.capabilities import CAPABILITY_CELLS, EXPRESSION_FLOOR_CELL
from polymer_claims.expression_floor_adapters import (
    ExpressionFloorHLAdapter,
    ExpressionFloorMeanAdapter,
    expression_floor_claim,
    expression_floor_oracle_registry,
    expression_floor_registry,
)
from polymer_claims.expression_floor_evidence import expression_floor_evalue
from polymer_claims.expression_floor_populate import preregister
from polymer_claims.evidence import _terminal_node
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract

_CTX = MaterializationContext(id="M", api_version="v1", data_version="d1")
_ADAPTERS = (ExpressionFloorMeanAdapter(), ExpressionFloorHLAdapter())


def _contract(tmp_path):
    pos = {f"p{i}": 95.0 + i for i in range(12)}
    neg = {f"n{i}": 0.0 for i in range(40)}
    fusion = {**{k: "fusion_pos" for k in pos}, **{k: "fusion_neg" for k in neg}}
    build_fusion_expr_contract({"RUNX1T1": {**pos, **neg}}, fusion, {k: "" for k in fusion},
                               genes=["RUNX1T1"], out_dir=tmp_path)
    _c.clear_contract_cache()
    return "se:tcga_laml_fusion_expr@1"


def test_expression_floor_cell_opts_into_requires_evidence():
    assert EXPRESSION_FLOOR_CELL.requires_evidence is True


def _run(tmp_path, *, with_evidence):
    ref = _contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        claim = expression_floor_claim("f", ref=ref, gene="RUNX1T1", floor=13.0, tissue="AML",
                                       search_cardinality=1)
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), [claim])
        ev = {"f": expression_floor_evalue(_terminal_node(claim))} if with_evidence else None
        out = run_cycle(corpus, _ADAPTERS, _CTX,
                        adapter_registry=expression_floor_registry(),
                        oracles=expression_floor_oracle_registry(),
                        evidence=ev, capability_registry=CAPABILITY_CELLS)
    return out.corpus.by_id()["f"].status


def test_no_evidence_does_not_license_a_data_channel_claim(tmp_path):
    assert _run(tmp_path, with_evidence=False) is not Status.LICENSED   # 3-way route refused


def test_with_evidence_licenses_the_same_claim(tmp_path):
    assert _run(tmp_path, with_evidence=True) is Status.LICENSED        # full 4-way gate
