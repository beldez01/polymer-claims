from polymer_protocol.adapter_registry import adapters_independent
from polymer_claims.bionemo.registry import bionemo_credential
from polymer_claims.bionemo.adapters import BioNeMoNIMAdapter
from tests.fixtures.synthetic_corroborator import SyntheticCorroboratorAdapter


def test_credential_records_nvidia_owner_and_sha256_hash():
    cred = bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim")
    assert cred.owner == "NVIDIA"
    assert cred.identity == "bionemo-nim"
    assert cred.implementation_hash.startswith("sha256:")
    assert cred.trusted is True


def test_bionemo_and_synthetic_are_independent():
    nvidia = bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim")
    synthetic = bionemo_credential(
        SyntheticCorroboratorAdapter, identity="synthetic-corroborator", owner="polymer-claims-test"
    )
    assert adapters_independent(nvidia, synthetic) is True


def test_same_class_pair_is_not_independent():
    a = bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim")
    b = bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim-2")
    assert adapters_independent(a, b) is False   # same owner AND same impl hash
