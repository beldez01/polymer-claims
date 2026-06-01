from polymer_grammar.status import PendingReason, Status


def test_package_imports():
    import polymer_grammar

    assert polymer_grammar.__version__ == "0.1.0"


def test_status_values():
    assert Status.LICENSED.value == "licensed"
    assert {s.value for s in Status} == {
        "conjectured",
        "exploratory",
        "pending",
        "licensed",
        "rejected",
    }


def test_pending_reasons_include_governance_and_incomparable():
    vals = {r.value for r in PendingReason}
    assert "unreproducible_by_governance" in vals
    assert "strength_incomparable" in vals
    assert "duhem_underdetermined" in vals
    assert len(vals) == 9
