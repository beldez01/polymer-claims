import json
import pytest
from polymer_grammar.capability import (
    ParamCodec, DataRefKind, data_ref_ok, SubjectRequirement, OracleRequirement,
    CapabilityRegistry, ConformanceResult, ConformanceReason, ConformanceWarning,
)
from polymer_grammar.verification_policy import VerificationPolicy


def _make_single_vp() -> VerificationPolicy:
    return VerificationPolicy(
        execution="single",
        result_rule="evalue_discovery",
        independence_requirement="baseline_ground_truth",
        evidence_policy_ref="sha256:" + "a" * 64,
        min_adapters=1,
    )


def _make_recompute_vp() -> VerificationPolicy:
    return VerificationPolicy(
        execution="recompute_pair",
        result_rule="criterion",
        independence_requirement="implementation",
        evidence_policy_ref=None,
        min_adapters=2,
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


# ---------------------------------------------------------------------------
# Task 9: content_hash + optional verification_policy + cardinality migration
# ---------------------------------------------------------------------------

def test_content_hash_prefixed(make_cell):
    """content_hash must start with 'sha256:'."""
    assert make_cell().content_hash.startswith("sha256:")


def test_content_hash_stable(make_cell):
    """Identical cells have the same content_hash."""
    assert make_cell().content_hash == make_cell().content_hash


def test_content_hash_changes_with_title(make_cell):
    """content_hash changes when a field (title) changes."""
    assert make_cell().content_hash != make_cell(title="other title").content_hash


def test_content_hash_changes_with_verification_policy(make_cell):
    """content_hash changes when verification_policy changes (None vs. recompute_pair)."""
    cell_none = make_cell()
    cell_vp = make_cell(verification_policy=_make_recompute_vp())
    assert cell_none.content_hash != cell_vp.content_hash


def test_model_dump_no_verification_policy_key_when_none(make_cell):
    """model_dump and model_dump_json must NOT include 'verification_policy' when it is None
    — byte-identical shape to pre-Task-9 serialization."""
    cell = make_cell()
    data = cell.model_dump(mode="json")
    assert "verification_policy" not in data
    data_json = json.loads(cell.model_dump_json())
    assert "verification_policy" not in data_json


def test_model_dump_includes_verification_policy_when_set(make_cell):
    """When verification_policy is set, it must appear in model_dump output."""
    cell = make_cell(verification_policy=_make_recompute_vp())
    data = cell.model_dump(mode="json")
    assert "verification_policy" in data
    assert data["verification_policy"]["execution"] == "recompute_pair"


def test_single_policy_with_min2_raises(make_cell):
    """verification_policy.execution='single' requires min_executing_adapters==1."""
    with pytest.raises(ValueError):
        make_cell(verification_policy=_make_single_vp(), min_executing_adapters=2)


def test_single_policy_with_min1_valid(make_cell):
    """verification_policy.execution='single' + min_executing_adapters==1 is valid."""
    cell = make_cell(
        verification_policy=_make_single_vp(),
        min_executing_adapters=1,
        eligible_adapter_identities=("p",),
    )
    assert cell.min_executing_adapters == 1
    assert cell.verification_policy is not None
    assert cell.verification_policy.execution == "single"


def test_recompute_pair_policy_with_min2_valid(make_cell):
    """verification_policy.execution='recompute_pair' + min_executing_adapters==2 remains valid."""
    cell = make_cell(verification_policy=_make_recompute_vp())
    assert cell.min_executing_adapters == 2


def test_no_policy_min2_still_valid(make_cell):
    """No verification_policy + min_executing_adapters==2 must remain valid (pre-Task-9 cells)."""
    cell = make_cell()  # default: no vp, min=2
    assert cell.min_executing_adapters == 2
    assert cell.verification_policy is None


def test_content_hash_single_policy_differs_from_no_policy(make_cell):
    """A cell with single policy has a different hash than same cell without policy."""
    cell_no_vp = make_cell()
    cell_single = make_cell(
        verification_policy=_make_single_vp(),
        min_executing_adapters=1,
        eligible_adapter_identities=("p",),
    )
    assert cell_no_vp.content_hash != cell_single.content_hash
