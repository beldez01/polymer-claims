from polymer_grammar import ValidationTier
from polymer_claims.bionemo.oracle import bionemo_oracle_registry


def test_oracle_registry_resolves_conservative_tier():
    reg = bionemo_oracle_registry(oracle_id="bionemo-plumbing@v1")
    dossier = reg.resolve("bionemo-plumbing@v1")
    assert dossier is not None
    assert dossier.validation_tier == ValidationTier.INDIRECT   # never ANCHORED for pure compute


def test_oracle_default_domain_is_unbounded():
    reg = bionemo_oracle_registry(oracle_id="bionemo-plumbing@v1")
    dossier = reg.resolve("bionemo-plumbing@v1")
    assert dossier.applicability_domain.subject_kinds == ()
