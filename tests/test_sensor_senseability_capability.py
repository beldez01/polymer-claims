"""End-to-end control test for the sensor::senseability@v1 capability (bridge C3 + C5).

The load-bearing deliverable: the two SensorKit known-answer controls run through the full
propose -> preregister -> license_batch flow and license/withhold as the geometry contract dictates,
via the two-classifier REPRODUCED route (SensorKit vs an independent reimplementation, no e-value):

  * R248Q  CCG->CCA @ var_index 2  -> tier "engineered" (ordinal 1) -> clears tier_bar 1 -> LICENSED
    at IndependenceTier.REPRODUCED.
  * R248W  CCG->CUG @ var_index 1  -> tier "unsenseable" (ordinal 0) -> below tier_bar 1 -> NOT
    LICENSED (withheld / refuted).
"""
from __future__ import annotations

from polymer_grammar import FDRLedger, Status
from polymer_grammar.licensing import IndependenceTier
from polymer_protocol import Corpus


def test_bind_resolves():
    from polymer_claims.capabilities import bind

    binding = bind("sensor::senseability", "v1")
    assert binding.trust_profile == "sensorkit-senseability-model-prediction"
    # both air-gapped legs are registered
    idents = {c.identity for c in binding.adapter_registry.credentials}
    assert idents == {"sensor-senseability-sensorkit", "sensor-senseability-reimpl"}
    # the two legs are a genuine independent pair (distinct owners + implementation hashes)
    from polymer_protocol.adapter_registry import pair_is_registry_independent
    assert pair_is_registry_independent(
        binding.adapter_registry,
        ("sensor-senseability-sensorkit", "sensor-senseability-reimpl"),
    )


def test_controls_license_and_withhold_reproduced():
    from polymer_claims.sensor_senseability_populate import (
        check_controls,
        license_batch,
        preregister,
        propose_control_claims,
    )

    claims = propose_control_claims()
    assert [c.id for c in claims] == ["sensor-R248Q", "sensor-R248W"]
    assert all(c.status is Status.PENDING for c in claims)

    corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
    # preregister locks NO e-LOND slot (no e-value route) — the ledger stays empty.
    assert corpus.fdr_ledger.n_tests == 0
    assert {c.id for c in corpus.claims} == {"sensor-R248Q", "sensor-R248W"}

    out = license_batch(corpus, claims)
    by = out.by_id()

    # R248Q: the positive control licenses via the two-classifier reproduction.
    r248q = by["sensor-R248Q"]
    assert r248q.status is Status.LICENSED
    assert r248q.licensing is not None
    assert r248q.licensing.independence_tier is IndependenceTier.REPRODUCED

    # R248W: the negative control is withheld (its tier is below the bar).
    r248w = by["sensor-R248W"]
    assert r248w.status is not Status.LICENSED

    rep = check_controls(out, positive="sensor-R248Q", negative="sensor-R248W")
    assert rep["ok"] is True
    assert rep["positive_licensed"] is True
    assert rep["negative_licensed"] is False
