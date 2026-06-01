import pytest
from pydantic import ValidationError

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import PendingReason, Status
from polymer_grammar.strength import StrengthVector


def _leaf():
    return QuantityLeaf(
        value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
        formula="ppcor::pcor.test(curvature, co_rate | gc)",
    )


def _strength(**kw):
    base = dict(
        magnitude=0.7, uncertainty=0.7, evidence_against_null=0.7,
        severity=0.7, world_contact=0.7, explanatory_virtue=0.7,
    )
    base.update(kw)
    return StrengthVector(**base)


def test_minimal_licensed_claim_builds():
    claim = Claim(
        id="recomb_curvature_co",
        title="Curvature disfavors crossover after GC control",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=[_leaf()],
        status=Status.LICENSED,
        strength=_strength(),
    )
    assert claim.schema_version == "v1.3"
    assert claim.pattern.id == "adjusted_effect"


def test_pending_status_requires_a_reason():
    with pytest.raises(ValidationError):
        Claim(
            id="x", title="t",
            pattern=PatternRef(id="adjusted_effect", version="v1"),
            leaves=[_leaf()], status=Status.PENDING,
        )


def test_pending_with_reason_is_valid():
    claim = Claim(
        id="x", title="t",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=[_leaf()], status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
    )
    assert claim.pending_reason == PendingReason.UNTESTED


def test_pending_reason_only_allowed_when_pending():
    with pytest.raises(ValidationError):
        Claim(
            id="x", title="t",
            pattern=PatternRef(id="adjusted_effect", version="v1"),
            leaves=[_leaf()], status=Status.LICENSED,
            pending_reason=PendingReason.UNTESTED,
        )


def test_claim_requires_at_least_one_leaf():
    with pytest.raises(ValidationError):
        Claim(
            id="x", title="t",
            pattern=PatternRef(id="adjusted_effect", version="v1"),
            leaves=[], status=Status.CONJECTURED,
        )
