import json
import pytest
from polymer_grammar.capability import (
    ParamCodec, DataRefKind, data_ref_ok, SubjectRequirement, OracleRequirement,
    CapabilityRegistry, ConformanceResult, ConformanceReason, ConformanceWarning,
)

def test_codecs_canonical_acceptance():
    assert ParamCodec(name="x", codec="string").is_canonical("anything ")
    assert ParamCodec(name="n", codec="int").is_canonical("5")
    assert not ParamCodec(name="n", codec="int").is_canonical("05")
    assert not ParamCodec(name="n", codec="int").is_canonical("+5")
    assert ParamCodec(name="a", codec="float").is_canonical("0.05")
    assert not ParamCodec(name="a", codec="float").is_canonical("5e-2")
    assert not ParamCodec(name="a", codec="float").is_canonical("nan")
    assert ParamCodec(name="p", codec="csv").is_canonical("a,b")
    assert not ParamCodec(name="p", codec="csv").is_canonical("a, b")
    assert not ParamCodec(name="p", codec="csv").is_canonical("a,,b")

def test_codec_validators():
    with pytest.raises(ValueError):
        ParamCodec(name="", codec="string")
    with pytest.raises(ValueError):
        ParamCodec(name="  ", codec="string")          # whitespace-only
    with pytest.raises(ValueError):
        ParamCodec(name="e", codec="enum")             # missing choices
    with pytest.raises(ValueError):
        ParamCodec(name="e", codec="enum", choices=("",))   # blank choice value
    with pytest.raises(ValueError):
        ParamCodec(name="e", codec="string", choices=("x",))

def test_data_ref_matchers():
    assert data_ref_ok(DataRefKind.OPAQUE, "dose_response")
    assert not data_ref_ok(DataRefKind.OPAQUE, "")
    assert data_ref_ok(DataRefKind.SE_CONTRACT, "se:tcga_laml_idh@2")
    for bad in ("se:a@b", "se:a@1@2", "se: x@1", "se:@1", "se:a@"):
        assert not data_ref_ok(DataRefKind.SE_CONTRACT, bad)

def test_subject_and_oracle_validators():
    SubjectRequirement(mode="forbidden")
    SubjectRequirement(mode="required", kind="genomic_region")
    with pytest.raises(ValueError):
        SubjectRequirement(mode="forbidden", kind="genomic_region")
    with pytest.raises(ValueError):
        SubjectRequirement(mode="optional", kind="not_a_kind")
    with pytest.raises(ValueError):
        OracleRequirement(default_oracle_id="   ")     # whitespace-only

def test_conformance_ok_derived_and_serialized():
    assert ConformanceResult().ok is True
    assert ConformanceResult(reasons=(ConformanceReason.PATTERN_MISMATCH,)).ok is False
    assert ConformanceResult(warnings=(ConformanceWarning.BINDING_ADAPTER_MISSING,)).ok is True
    assert json.loads(ConformanceResult().model_dump_json())["ok"] is True

def test_cell_ref_and_invariants(make_cell):
    assert make_cell().ref == "x::y@v1"
    for bad in [dict(title="  "), dict(allowed_comparators=()),
                dict(eligible_adapter_identities=("p", "p")),
                dict(eligible_adapter_identities=("p", " ")),
                dict(min_executing_adapters=3), dict(claim_leaf_kinds=()),
                dict(param_schema=(ParamCodec(name="a", codec="string"),
                                   ParamCodec(name="a", codec="int")))]:
        with pytest.raises(ValueError):
            make_cell(**bad)

def test_registry_resolve_and_duplicate_guard(make_cell):
    a, b = make_cell(), make_cell(capability_version="v2")
    reg = CapabilityRegistry(cells=(a, b))
    assert reg.resolve("x::y", "v2") is b and reg.resolve("x::y", "v9") is None and not reg.is_empty
    with pytest.raises(ValueError):
        CapabilityRegistry(cells=(a, a))
