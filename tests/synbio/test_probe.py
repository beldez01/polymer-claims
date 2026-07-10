"""Task 6 — the probe harness: build all five claims and emit the structured probe report."""
from polymer_grammar.status import Status

from polymer_claims.synbio.probe import build_all, probe_report


def test_build_all_returns_five_validated_conjectured_claims():
    claims = build_all()
    assert len(claims) == 5
    # Construction through the grammar validates each; all are reported → CONJECTURED.
    assert all(c.status is Status.CONJECTURED for c in claims)
    assert len({c.id for c in claims}) == 5


def test_probe_report_enumerates_claims_and_gaps():
    rep = probe_report()
    assert len(rep["claims"]) == 5
    for entry in rep["claims"]:
        assert entry["leaf_kind"]
        assert entry["validated"] is True
        assert entry["status"] == "conjectured"
        assert entry["source"]
    gap_ids = {g["id"] for g in rep["gaps"]}
    assert {"GAP-1", "GAP-2", "GAP-3", "GAP-4"} <= gap_ids
    # The two general-class gaps (context, interval) are the headline finds.
    general = {g["id"] for g in rep["gaps"] if g["expansion_class"] == "general"}
    assert general == {"GAP-2", "GAP-3"}


def test_probe_covers_all_four_leaf_kinds_used():
    kinds = {e["leaf_kind"] for e in probe_report()["claims"]}
    # C1 FUNDAMENTAL, C2/C3/C4 DERIVED quantities, C5 proposition.
    assert "quantity" in kinds
    assert "proposition" in kinds
