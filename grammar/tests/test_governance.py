import pytest
from pydantic import ValidationError

from polymer_grammar.governance import (
    AccessScope,
    Governance,
    HazardClass,
    blocks_reproduction,
    requires_safety_review,
)


def test_bare_governance_is_public_no_hazard():
    g = Governance()
    assert g.hazard_class == HazardClass.NONE
    assert g.access_scope == AccessScope.PUBLIC
    assert g.note is None


def test_governance_constructs_and_is_hashable():
    g = Governance(hazard_class=HazardClass.DUAL_USE, access_scope=AccessScope.CONTROLLED,
                   note="EGA controlled-access")
    assert g.hazard_class == HazardClass.DUAL_USE
    assert isinstance(hash(g), int)
    with pytest.raises(ValidationError):
        Governance(bogus=1)


def test_blocks_reproduction_over_all_access_scopes():
    expected = {
        AccessScope.PUBLIC: False, AccessScope.REGISTERED_ACCESS: False,
        AccessScope.CONTROLLED: False, AccessScope.RESTRICTED: True, AccessScope.EMBARGOED: True,
    }
    for scope, blocks in expected.items():
        assert blocks_reproduction(Governance(access_scope=scope)) is blocks


def test_requires_safety_review_over_all_hazard_classes():
    expected = {
        HazardClass.NONE: False, HazardClass.LOW: False, HazardClass.MODERATE: False,
        HazardClass.HIGH: True, HazardClass.DUAL_USE: True,
    }
    for hz, review in expected.items():
        assert requires_safety_review(Governance(hazard_class=hz)) is review
