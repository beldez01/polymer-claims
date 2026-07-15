"""GTEx healthy-tissue safety atlas (Ch2) — the ingest builder + a REAL-DATA license smoke test.

The committed `gtex_healthy@1` contract carries a real GTEx v10 panel, so the absence capability is
exercised end-to-end on genuine data: MAGEA4 (testis-restricted) licenses below a 50 TPM ceiling; ACTB
(housekeeping, ~8000 TPM) is vetoed by the max leg.
"""
from __future__ import annotations

import gzip

from polymer_grammar import FDRLedger, Status
from polymer_protocol import Corpus

from polymer_claims import contracts as _c
from polymer_claims.ingest.gtex_healthy import _read_gct_panel, build_gtex_healthy_contract


def _synthetic_gct(tmp_path):
    p = tmp_path / "mini.gct.gz"
    rows = [
        "#1.2", "3\t2",
        "Name\tDescription\tTissueA\tTissueB",
        "ENSG1\tGENEHI\t100.0\t200.0",
        "ENSG2\tGENELO\t0.0\t1.5",
        "ENSG3\tOTHER\t5.0\t5.0",
    ]
    p.write_bytes(gzip.compress(("\n".join(rows) + "\n").encode()))
    return p


def test_read_gct_panel_subsets_by_symbol(tmp_path):
    tissues, panel = _read_gct_panel(_synthetic_gct(tmp_path), {"GENEHI", "GENELO"})
    assert tissues == ["TissueA", "TissueB"]
    assert panel["GENEHI"] == {"TissueA": 100.0, "TissueB": 200.0}
    assert "OTHER" not in panel                      # not requested -> not read (no fabrication)


def test_duplicate_symbol_aggregates_by_max_not_first(tmp_path):
    # AUDIT finding 5: a safety veto must never silently drop the high-expression duplicate row.
    p = tmp_path / "dup.gct.gz"
    rows = [
        "#1.2", "2\t2",
        "Name\tDescription\tTissueA\tTissueB",
        "ENSG1a\tDUP\t1.0\t2.0",       # benign row (would win under "first wins")
        "ENSG1b\tDUP\t9.0\t0.5",       # high-expression row — must not be dropped
    ]
    p.write_bytes(gzip.compress(("\n".join(rows) + "\n").encode()))
    _tissues, panel = _read_gct_panel(p, {"DUP"})
    assert panel["DUP"] == {"TissueA": 9.0, "TissueB": 2.0}   # per-tissue MAX across duplicate rows


def test_duplicate_max_is_nan_safe(tmp_path):
    # AUDIT r2 finding 2: a NaN in the first duplicate row must not hide a later high finite value.
    p = tmp_path / "nan.gct.gz"
    rows = [
        "#1.2", "2\t1", "Name\tDescription\tTissueA",
        "ENSG1a\tDUP\tnan",            # NaN first — must be skipped, not max'd
        "ENSG1b\tDUP\t9.0",            # the real high value
    ]
    p.write_bytes(gzip.compress(("\n".join(rows) + "\n").encode()))
    _tissues, panel = _read_gct_panel(p, {"DUP"})
    assert panel["DUP"] == {"TissueA": 9.0}   # NaN skipped, finite value kept (not nan)


def test_builder_writes_a_resolvable_contract(tmp_path):
    build_gtex_healthy_contract(_synthetic_gct(tmp_path), genes=["GENEHI", "GENELO"], out_dir=tmp_path)
    with _c.using_contract_root(tmp_path):
        se = _c.load_contract("se:gtex_healthy@1")
        m = _c.load_manifest(se)
    assert [c["Sample_Group"] for c in m["col_data"]] == ["healthy", "healthy"]
    assert {c["tissue"] for c in m["col_data"]} == {"TissueA", "TissueB"}


def test_absence_licenses_a_restricted_target_vetoes_housekeeping_on_real_gtex():
    from polymer_claims.expression_absence_adapters import expression_absence_claim
    from polymer_claims.expression_absence_populate import license_batch, preregister

    ref = "se:gtex_healthy@1"        # the committed real GTEx panel
    claims = [
        expression_absence_claim("absence-MAGEA4", ref=ref, gene="MAGEA4", ceiling=50.0, search_cardinality=1),
        expression_absence_claim("absence-ACTB", ref=ref, gene="ACTB", ceiling=50.0, search_cardinality=1),
    ]
    corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
    out = license_batch(corpus, claims, ref=ref).by_id()
    assert out["absence-MAGEA4"].status is Status.LICENSED         # testis-restricted -> safe below 50 TPM
    assert out["absence-ACTB"].status is not Status.LICENSED       # ~8000 TPM -> vetoed by the max leg
