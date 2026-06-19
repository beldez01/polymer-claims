from polymer_grammar import (
    GenerationMode,
    PendingReason,
    Provenance,
    SeverityProvenance,
)
from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)


def test_prior_cohorts_defaults_empty_and_accepts_tuple():
    p = Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=1)
    assert p.prior_cohorts == ()
    p2 = Provenance(
        generated_by=GenerationMode.LITERATURE_EXTRACTED,
        search_cardinality=1,
        prior_cohorts=("cohortA", "cohortB"),
    )
    assert p2.prior_cohorts == ("cohortA", "cohortB")


def _sat(dimnames: str | None = None) -> Satisfaction:
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id="M1", api_version="v1", data_version="d1", dimnames_hash=dimnames
        ),
    )


def test_licensing_severity_provenance_defaults_none_and_accepts_enum():
    lic = Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(_sat(),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
    )
    assert lic.severity_provenance is None
    lic2 = lic.model_copy(update={"severity_provenance": SeverityProvenance.CONFIRMATORY})
    assert lic2.severity_provenance is SeverityProvenance.CONFIRMATORY


def test_pending_reason_has_shared_cause_member():
    assert PendingReason.SHARED_CAUSE_CONFIRMATORY.value == "shared_cause_confirmatory"
