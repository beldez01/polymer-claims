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
    assert "materialization_drifted" in vals
    assert len(vals) == 10


def test_materialization_drifted_reason_carried_on_a_pending_claim():
    from polymer_grammar import CategoricalLeaf, Claim, PatternRef

    claim = Claim(
        id="c",
        title="c",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="t"),),
        status=Status.PENDING,
        pending_reason=PendingReason.MATERIALIZATION_DRIFTED,
    )
    assert claim.pending_reason is PendingReason.MATERIALIZATION_DRIFTED
    assert claim.pending_reason.value == "materialization_drifted"
