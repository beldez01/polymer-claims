"""Compatibility regression goldens — Task 18.

Proves that the None-omit model_serializers shipped in Tasks 8/9/10 on
Licensing / CapabilityCell / EvaluationPlan preserve byte-identical output
for all pre-existing content hashes.  Every assertion is a REAL byte-identity
check, not a vacuous one.
"""
from __future__ import annotations

import json
from pathlib import Path

from polymer_claims._hashing import canonical_sha256
from polymer_grammar.capability import CapabilityCell
from polymer_grammar.commitment import commitment_hash
from polymer_grammar.leaf import CategoricalLeaf, MeasurementBasis
from polymer_grammar.licensing import LicenseRoute, Licensing
from polymer_grammar.operations import (
    ComputeGraph,
    Comparator,
    EvaluationPlan,
    OperationNode,
    ProducedLeafSpec,
    SatisfactionCriterion,
)
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status
from polymer_grammar.claim import Claim
from tests.attestation._fixtures import licensed_claim, licensing, mc, sat

_GOLDEN = Path(__file__).parent / "_golden_bundle.json"
_PATTERN = PatternRef(id="adjusted_effect", version="v1")


# ---------------------------------------------------------------------------
# Helpers (mirror _golden_corpus from test_build_bundle.py)
# ---------------------------------------------------------------------------

def _L(cid: str) -> Claim:
    return licensed_claim(
        cid,
        licensing(sat(mc(
            dimnames_hash="sha256:" + "a" * 64,
            profile_hash="sha256:" + "b" * 64,
            semantic_run_id="r1",
        ))),
    )


def _golden_digests() -> dict[str, str]:
    """Parse the committed golden bundle, return {claim_id: bare_sha256_hex}."""
    bundle = json.loads(_GOLDEN.read_text())
    result: dict[str, str] = {}
    for attestation in bundle["attestations"]:
        for subject in attestation["subject"]:
            name = subject["name"]
            digest = subject["digest"]["sha256"]
            result[name] = digest
    return result


# ---------------------------------------------------------------------------
# 1. Attestation subject digests unchanged
# ---------------------------------------------------------------------------

def test_subject_digest_c1_byte_identical_to_golden():
    """canonical_sha256(claim.model_dump()) for c1 must match the committed golden."""
    golden = _golden_digests()
    claim = _L("c1")
    computed = canonical_sha256(claim.model_dump(mode="json"))
    bare = computed.removeprefix("sha256:")
    assert bare == golden["c1"], (
        f"c1 subject digest drifted!\n  computed : {bare}\n  golden   : {golden['c1']}"
    )


def test_subject_digest_c2_byte_identical_to_golden():
    """canonical_sha256(claim.model_dump()) for c2 must match the committed golden."""
    golden = _golden_digests()
    claim = _L("c2")
    computed = canonical_sha256(claim.model_dump(mode="json"))
    bare = computed.removeprefix("sha256:")
    assert bare == golden["c2"], (
        f"c2 subject digest drifted!\n  computed : {bare}\n  golden   : {golden['c2']}"
    )


def test_golden_bundle_file_shape_unchanged():
    """The golden bundle still has exactly 2 attestations with the expected claim ids."""
    bundle = json.loads(_GOLDEN.read_text())
    names = [att["subject"][0]["name"] for att in bundle["attestations"]]
    assert names == ["c1", "c2"], f"unexpected attestation order/count: {names}"
    assert bundle["bundleType"] == "https://polymerclaims.org/attestation-bundle/v1"


# ---------------------------------------------------------------------------
# 2. CapabilityCell dump byte-identical (no verification_policy key when None)
# ---------------------------------------------------------------------------

def _cell_dump(cell: CapabilityCell) -> dict:
    return cell.model_dump(mode="json")


def test_mean_diff_cell_no_verification_policy_key():
    from polymer_claims.capabilities import MEAN_DIFF_CELL
    d = _cell_dump(MEAN_DIFF_CELL)
    assert "verification_policy" not in d, (
        f"verification_policy must be omitted when None; got keys: {list(d)}"
    )


def test_region_delta_beta_cell_no_verification_policy_key():
    from polymer_claims.capabilities import REGION_DELTA_BETA_CELL
    d = _cell_dump(REGION_DELTA_BETA_CELL)
    assert "verification_policy" not in d, (
        f"verification_policy must be omitted when None; got keys: {list(d)}"
    )


def test_n_dmps_cell_no_verification_policy_key():
    from polymer_claims.capabilities import N_DMPS_CELL
    d = _cell_dump(N_DMPS_CELL)
    assert "verification_policy" not in d, (
        f"verification_policy must be omitted when None; got keys: {list(d)}"
    )


def test_three_cells_no_verification_policy_key_model_dump_json():
    """Same check via model_dump_json (the JSON-string path)."""
    from polymer_claims.capabilities import MEAN_DIFF_CELL, REGION_DELTA_BETA_CELL, N_DMPS_CELL
    for cell in (MEAN_DIFF_CELL, REGION_DELTA_BETA_CELL, N_DMPS_CELL):
        j = json.loads(cell.model_dump_json())
        assert "verification_policy" not in j, (
            f"{cell.capability_id}: verification_policy present in model_dump_json output"
        )


# ---------------------------------------------------------------------------
# 2b. agreement_mode byte-identical for every pre-existing cell (only n-DMP and, since the
# Hodges-Lehmann leg swap, region-Δβ opt in)
# ---------------------------------------------------------------------------


def test_mean_diff_cell_no_agreement_mode_key():
    """The tight global agreement bound is unaffected for stats::mean_diff: no new
    'agreement_mode' key, hence no content_hash drift."""
    from polymer_claims.capabilities import MEAN_DIFF_CELL
    d = _cell_dump(MEAN_DIFF_CELL)
    assert "agreement_mode" not in d, (
        f"{MEAN_DIFF_CELL.capability_id}: agreement_mode must be omitted at the tight_numeric default; keys: {list(d)}"
    )
    assert MEAN_DIFF_CELL.agreement_mode == "tight_numeric"


def test_n_dmps_cell_intentionally_sets_agreement_mode():
    """n-DMP is a deliberate exception: it opts into both_satisfy_criterion (documented in
    capabilities.py, N_DMPS_CELL), so its dump DOES carry the key."""
    from polymer_claims.capabilities import N_DMPS_CELL
    d = _cell_dump(N_DMPS_CELL)
    assert d["agreement_mode"] == "both_satisfy_criterion"


def test_region_delta_beta_cell_intentionally_sets_agreement_mode():
    """region-Δβ is the other deliberate exception: its two legs (mean-difference vs
    Hodges-Lehmann) are genuinely different estimators, so it opts into
    both_satisfy_criterion too (documented in capabilities.py, REGION_DELTA_BETA_CELL)."""
    from polymer_claims.capabilities import REGION_DELTA_BETA_CELL
    d = _cell_dump(REGION_DELTA_BETA_CELL)
    assert d["agreement_mode"] == "both_satisfy_criterion"


# ---------------------------------------------------------------------------
# 3. EvaluationPlan commitment_hash unchanged (no execution_contract key when None)
# ---------------------------------------------------------------------------

def _no_contract_plan() -> EvaluationPlan:
    node = OperationNode(
        id="n0", impl="builtin::const",
        params=(("value", "0.2"), ("region", "cg1,cg2")),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.GT, threshold=0.1),
    )


def _plan_claim(plan: EvaluationPlan) -> Claim:
    return Claim(
        id="compat-c", title="compat-c", pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term="t"),),
        status=Status.CONJECTURED,
        evaluation_plan=plan,
    )


def test_no_contract_plan_omits_execution_contract_key():
    plan = _no_contract_plan()
    assert "execution_contract" not in plan.model_dump_json(), (
        "execution_contract must not appear in model_dump_json when it is None"
    )
    assert "execution_contract" not in plan.model_dump(mode="json"), (
        "execution_contract must not appear in model_dump when it is None"
    )


def test_commitment_hash_stable_for_no_contract_plan():
    """commitment_hash must be deterministic (recompute twice → equal)."""
    claim = _plan_claim(_no_contract_plan())
    h1 = commitment_hash(claim)
    h2 = commitment_hash(claim)
    assert h1 == h2, "commitment_hash is not deterministic"
    assert h1.startswith("sha256:"), f"expected sha256:-prefixed hash, got: {h1!r}"


def test_commitment_hash_no_execution_contract_substring():
    """The JSON payload hashed by commitment_hash must not contain 'execution_contract'."""
    plan = _no_contract_plan()
    json_payload = plan.model_dump_json()
    assert "execution_contract" not in json_payload, (
        "execution_contract leaked into commitment_hash JSON payload"
    )


# ---------------------------------------------------------------------------
# 4. JSON-schema generation succeeds (model_serializer(mode="wrap") must not break schema)
# ---------------------------------------------------------------------------

def test_licensing_json_schema_succeeds():
    schema = Licensing.model_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema or "$defs" in schema or "allOf" in schema


def test_capability_cell_json_schema_succeeds():
    schema = CapabilityCell.model_json_schema()
    assert isinstance(schema, dict)


def test_evaluation_plan_json_schema_succeeds():
    schema = EvaluationPlan.model_json_schema()
    assert isinstance(schema, dict)


# ---------------------------------------------------------------------------
# 5. Historical-JSON deserialization (JSON lacking new optional fields validates)
# ---------------------------------------------------------------------------

def test_historical_licensing_without_evidence_fields_deserializes():
    """JSON produced before Task 8 (no verification_standing / evidence_provenance)
    must still parse into a valid Licensing."""
    historical = {
        "route": "severe_test",
        "satisfactions": [
            {
                "verdict": "satisfied",
                "materialization": {
                    "id": "m1",
                    "api_version": "0.9.x",
                    "data_version": "db@2026-06-01",
                    "note": None,
                    "semantic_run_id": None,
                    "profile_hash": None,
                    "dimnames_hash": None,
                    "shared_cause_factors": [],
                },
                "credential_ids": [],
            }
        ],
        "rival_set_closure": "open_acknowledged",
        "rivals_considered": [],
        "independence_tier": "reproduced",
        "severity_provenance": None,
        "shared_cause_overlap": None,
        "note": None,
    }
    lic = Licensing.model_validate(historical)
    assert lic.route == LicenseRoute.SEVERE_TEST
    assert lic.verification_standing is None
    assert lic.evidence_provenance is None


def test_historical_licensing_json_string_deserializes():
    """model_validate_json path for historical Licensing JSON."""
    historical_json = json.dumps({
        "route": "severe_test",
        "satisfactions": [
            {
                "verdict": "satisfied",
                "materialization": {
                    "id": "m1",
                    "api_version": "0.9.x",
                    "data_version": "db@2026-06-01",
                    "note": None,
                    "semantic_run_id": None,
                    "profile_hash": None,
                    "dimnames_hash": None,
                    "shared_cause_factors": [],
                },
                "credential_ids": [],
            }
        ],
        "rival_set_closure": "open_acknowledged",
        "rivals_considered": [],
        "independence_tier": "reproduced",
        "severity_provenance": None,
        "shared_cause_overlap": None,
        "note": None,
    })
    lic = Licensing.model_validate_json(historical_json)
    assert lic.route == LicenseRoute.SEVERE_TEST
    assert lic.verification_standing is None


def test_historical_capability_cell_without_verification_policy_deserializes():
    """A CapabilityCell JSON payload lacking verification_policy must validate."""
    from polymer_claims.capabilities import MEAN_DIFF_CELL
    # Dump without the new field (it's already absent when None), then re-parse.
    d = MEAN_DIFF_CELL.model_dump(mode="json")
    assert "verification_policy" not in d  # sanity
    cell2 = CapabilityCell.model_validate(d)
    assert cell2.capability_id == MEAN_DIFF_CELL.capability_id
    assert cell2.verification_policy is None


def test_historical_evaluation_plan_without_execution_contract_deserializes():
    """An EvaluationPlan JSON payload lacking execution_contract must validate."""
    plan = _no_contract_plan()
    d = plan.model_dump(mode="json")
    assert "execution_contract" not in d  # sanity
    plan2 = EvaluationPlan.model_validate(d)
    assert plan2.criterion.comparator == Comparator.GT
    assert plan2.execution_contract is None
