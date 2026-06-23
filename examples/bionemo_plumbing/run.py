"""End-to-end plumbing: a cached BioNeMo NIM run + a fenced synthetic corroborator drive ONE
claim to LICENSED, offline. Deferred-wedge: the metric here is a neutral plumbing score."""
from __future__ import annotations

import json
from pathlib import Path

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    DataHandle,
    EvaluationPlan,
    FDRLedger,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    SatisfactionCriterion,
    Status,
)
from polymer_protocol import AdapterRegistry, Corpus, run_cycle

from polymer_claims.bionemo.adapters import BioNeMoNIMAdapter
from polymer_claims.bionemo.apparatus import BioNeMoApparatus, build_materialization_context
from polymer_claims.bionemo.client import NimClient, NimRequest, NimResponse
from polymer_claims.bionemo.registry import bionemo_credential
from polymer_claims.attestation import build_certificate  # noqa: E402
from polymer_claims.bionemo.oracle import bionemo_oracle_registry  # noqa: E402

import sys

# import the fenced fixture (lives under tests/, not shipped in the package)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.fixtures.synthetic_corroborator import SyntheticCorroboratorAdapter  # noqa: E402

_IMPL = "bionemo::plumbing"
_CLAIM_ID = "bionemo-plumbing-1"
_ORACLE_ID = "bionemo-plumbing@v1"
_CASSETTE = Path(__file__).with_name("cassette.json")


def _cassette_transport(req: NimRequest, api_key: str) -> NimResponse:
    rec = json.loads(_CASSETTE.read_text())
    return NimResponse(status=rec["status"], body=rec["body"], model_version=rec["model_version"])


def _claim(oracle_ref=None) -> Claim:
    node = OperationNode(
        id="n0",
        impl=_IMPL,
        inputs=(DataHandle(ref="seq1"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
        oracle_ref=oracle_ref,
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.5),
    )
    return Claim(
        id=_CLAIM_ID,
        title="BioNeMo plumbing claim",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="plumbing"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        evaluation_plan=plan,
    )


def run_plumbing(cache_dir, *, with_oracle: bool = False):
    cassette = json.loads(_CASSETTE.read_text())
    score = cassette["body"]["out"]["score"]

    apparatus = BioNeMoApparatus(
        endpoint="https://example/nim/plumbing",
        model_id="plumbing-nim",
        model_version=cassette["model_version"],
        payload_schema=("sequence",),
    )
    ctx = build_materialization_context(apparatus, id="M1", api_version="v1", data_version="d1")

    client = NimClient(transport=_cassette_transport, cache_dir=Path(cache_dir), api_key="cassette")
    bionemo = BioNeMoNIMAdapter(
        client,
        impl=_IMPL,
        endpoint=apparatus.endpoint,
        value_path=("out", "score"),
        substrate={"seq1": {"sequence": "MAAAAA"}},
        identity="bionemo-nim",
    )
    corroborator = SyntheticCorroboratorAdapter(impl=_IMPL, value=score)

    registry = AdapterRegistry(
        credentials=(
            bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim"),
            bionemo_credential(
                SyntheticCorroboratorAdapter,
                identity="synthetic-corroborator",
                owner="polymer-claims-test",
            ),
        )
    )

    oracle_ref = _ORACLE_ID if with_oracle else None
    corpus = Corpus(claims=(_claim(oracle_ref=oracle_ref),), fdr_ledger=FDRLedger(target_fdr=0.05))
    oracles = bionemo_oracle_registry(oracle_id=_ORACLE_ID) if with_oracle else None
    return run_cycle(corpus, (bionemo, corroborator), ctx, oracles=oracles, adapter_registry=registry)


def certify_plumbing(cache_dir):
    """Run the plumbing loop, then build a single-claim certificate. Statements are
    reconstructed on-demand from the LICENSED claim's licensing field (run_cycle does not
    store them), so a plain corpus is all build_certificate needs."""
    result = run_plumbing(cache_dir=cache_dir)
    return build_certificate(result.corpus, _CLAIM_ID, ledger=None, target_q=0.05)


if __name__ == "__main__":  # pragma: no cover
    import tempfile

    res = run_plumbing(cache_dir=tempfile.mkdtemp())
    print(res.corpus.by_id()[_CLAIM_ID].status)
