import pytest
from pydantic import ValidationError

from polymer_grammar.provenance import GenerationMode, Provenance


def test_human_authored_provenance_constructs():
    p = Provenance(generated_by=GenerationMode.HUMAN_AUTHORED, search_cardinality=1)
    assert p.generated_by == GenerationMode.HUMAN_AUTHORED
    assert p.search_cardinality == 1
    assert p.agent_id is None
    assert p.preregistration_hash is None


def test_agent_generated_requires_agent_id():
    ok = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="claude-opus-4-8",
                    search_cardinality=40)
    assert ok.agent_id == "claude-opus-4-8"
    with pytest.raises(ValidationError):
        Provenance(generated_by=GenerationMode.AGENT_GENERATED, search_cardinality=40)  # no agent_id


def test_search_cardinality_must_be_at_least_one():
    with pytest.raises(ValidationError):
        Provenance(generated_by=GenerationMode.HUMAN_AUTHORED, search_cardinality=0)


def test_provenance_carries_optional_prereg_hash_and_is_hashable():
    p = Provenance(generated_by=GenerationMode.LITERATURE_EXTRACTED, search_cardinality=1,
                   preregistration_hash="sha256-deadbeef", method="manual-curation")
    assert p.preregistration_hash == "sha256-deadbeef"
    assert isinstance(hash(p), int)
    with pytest.raises(ValidationError):
        Provenance(generated_by=GenerationMode.HUMAN_AUTHORED, search_cardinality=1, bogus=1)


def test_public_api_exports():
    import polymer_grammar as pg

    for name in [
        "GenerationMode", "Provenance", "HazardClass", "AccessScope", "Governance",
        "blocks_reproduction", "requires_safety_review",
    ]:
        assert hasattr(pg, name), f"{name} not exported from polymer_grammar"
