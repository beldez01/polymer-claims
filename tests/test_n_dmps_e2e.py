from __future__ import annotations

import json
import tempfile
from pathlib import Path

from polymer_grammar import FDRLedger, IndependenceTier, MaterializationContext, PendingReason, Status
from polymer_protocol import AdapterCredential, AdapterRegistry, Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.capabilities import CAPABILITY_CELLS
from polymer_claims.contracts import clear_contract_cache, using_contract_root
from polymer_claims.evidence import evidence_map
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_ndmp import NDmpRankAdapter, NDmpTTestAdapter, n_dmps_claim, ndmp_independent_registry
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (NDmpTTestAdapter(), NDmpRankAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_POWERED = "se:epicv2_casectrl_powered@1"
_NULL_PROBES = tuple(f"cg{i:08d}" for i in range(11, 25))  # control region only (no signal)


def _run(claim):
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    return run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=ndmp_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE),
        evidence=evidence_map(corpus),
        capability_registry=CAPABILITY_CELLS,
    )


def test_n_dmps_over_signal_licenses_reproduced():
    claim = n_dmps_claim("c-ndmp", ref=_POWERED, k=3)  # all 24 probes
    result = _run(claim)
    c = next(x for x in result.corpus.claims if x.id == "c-ndmp")
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPRODUCED
    assert result.corpus.fdr_ledger.n_tests == 1
    assert result.corpus.fdr_ledger.n_discoveries == 1


def test_n_dmps_over_null_region_does_not_license():
    # THE MONEY-SHOT: only control probes -> count 0 < k=3 -> criterion (GE 3) unmet -> REJECTED.
    claim = n_dmps_claim("c-null", ref=_POWERED, probes=_NULL_PROBES, k=3)
    result = _run(claim)
    c = next(x for x in result.corpus.claims if x.id == "c-null")
    assert c.status == Status.REJECTED


def test_same_owner_pair_held_pending():
    same_owner = AdapterRegistry(credentials=(
        AdapterCredential(identity="methyl-ndmp-ttest", owner="o", implementation_hash="h1"),
        AdapterCredential(identity="methyl-ndmp-rank", owner="o", implementation_hash="h2"),
    ))
    claim = n_dmps_claim("c-ndmp", ref=_POWERED, k=3)
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus, _ADAPTERS, _BASE, adapter_registry=same_owner,
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE), evidence=evidence_map(corpus),
    )
    c = next(x for x in result.corpus.claims if x.id == "c-ndmp")
    # air-gap: same owner -> not registry-independent -> held PENDING (not licensed)
    assert c.status == Status.PENDING
    assert c.pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT


# ---------------------------------------------------------------------------
# TDD (c): the two legs genuinely DISAGREE on whether the criterion is met on a purpose-built
# adversarial contract -> the air-gap fails and the claim is held PENDING (not licensed).
#
# Under agreement_mode="both_satisfy_criterion" (n-DMP's mode), agreement no longer requires
# the two legs' raw counts to be numerically close -- it requires each leg's OWN count to
# independently satisfy the claim's criterion. So the only way this adversarial contract can
# still demonstrate disagreement is a genuine VERDICT split: one leg's count clears k, the
# other's doesn't.
# ---------------------------------------------------------------------------

# na=10/nb=10 outlier-laden probe from test_methyl_ndmp.py's
# test_pooled_t_and_rank_disagree_on_an_outlier_laden_probe: pooled-t says NOT a DMP (p~0.76,
# outlier-inflated variance), rank-sum says IS a DMP (p~0.003, robust to the outlier's magnitude).
_ADV_A = [0.2030, 0.1896, 0.2075, 0.2094, 0.1805, 0.1870, 0.2013, 0.1968, 0.1998, 0.9900]
_ADV_B = [0.2415, 0.2588, 0.2578, 0.2507, 0.2613, 0.2547, 0.2414, 0.2537, 0.2404, 0.2588]
_NULL_A = [0.20] * 10
_NULL_B = [0.20] * 10  # identical -> both legs agree: not a DMP


def _write_adversarial_contract(root: Path) -> None:
    """5-probe SE-Contract (4 null probes both legs agree are not DMPs + 1 adversarial probe
    the legs disagree on) so leg A's count (0) and leg B's count (1) diverge."""
    sample_ids = [f"s{i:03d}" for i in range(1, 21)]
    col_data = [
        {"sample_id": sid, "Sample_Group": "level1" if i < 10 else "level2"}
        for i, sid in enumerate(sample_ids)
    ]
    probes = ["pnull1", "pnull2", "pnull3", "pnull4", "padv"]
    manifest = {
        "uid": "ndmp_tolerance_adversarial@1",
        "assays": [{"name": "beta", "ref": "ndmp_tolerance_adversarial.betas.tsv"}],
        "col_data": col_data,
        "row_data": [{"feature_id": p} for p in probes],
        "metadata": {"genome_assembly": "hg38"},
    }
    (root / "ndmp_tolerance_adversarial.json").write_text(json.dumps(manifest))
    lines = ["feature_id\t" + "\t".join(sample_ids)]
    for p in probes:
        vals = (_ADV_A + _ADV_B) if p == "padv" else (_NULL_A + _NULL_B)
        lines.append(p + "\t" + "\t".join(repr(v) for v in vals))
    (root / "ndmp_tolerance_adversarial.betas.tsv").write_text("\n".join(lines) + "\n")


def test_two_legs_disagree_on_criterion_holds_claim_pending():
    ref = "se:ndmp_tolerance_adversarial@1"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_adversarial_contract(root)
        with using_contract_root(root):
            clear_contract_cache()
            # k=1, comparator GE: leg A's count (0) REFUTES (0 >= 1 is false) while leg B's
            # count (1) SATISFIES (1 >= 1 is true) -- a genuine verdict split, so agreement
            # fails under both_satisfy_criterion (no numeric-closeness escape hatch: this
            # isn't about the counts being far apart, it's that only one leg clears k at all).
            claim = n_dmps_claim(
                "c-adv", ref=ref, probes=("pnull1", "pnull2", "pnull3", "pnull4", "padv"), k=1,
            )
            result = _run(claim)
            clear_contract_cache()
    c = next(x for x in result.corpus.claims if x.id == "c-adv")
    assert c.status == Status.PENDING
    assert c.licensing is None
