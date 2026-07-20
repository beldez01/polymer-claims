"""Pre-register + license the sensor::senseability controls through run_cycle (bridge C5).

Mirrors expression_floor_populate, but the sensor capability licenses via the two-classifier
REPRODUCED route with NO e-value (its cell does not set requires_evidence). So:
  * preregister admits the PENDING claims via the invariance precondition and appends them to the
    corpus — it locks NO e-LOND slot (there is no e-value test to register).
  * license_batch runs one PER-CLAIM-ISOLATED run_cycle with the two air-gapped adapters, a single
    MaterializationContext (→ IndependenceTier.REPRODUCED), and evidence=None.

Umbrella/impure; NOT re-exported from __init__.
"""
from __future__ import annotations

from polymer_grammar import Claim, GenomicRegion, MaterializationContext
from polymer_protocol import Corpus, run_cycle

from .capabilities import CAPABILITY_CELLS
from .evidence import _terminal_node
from .invariance import admit_by_invariance
from .expression_floor_populate import ControlCheckFailed, check_controls
from .sensor_senseability_adapters import (
    SensorSenseabilityReimplAdapter,
    SensorSenseabilitySensorKitAdapter,
    sensor_senseability_claim,
    sensor_senseability_oracle_registry,
    sensor_senseability_registry,
)

__all__ = [
    "ControlCheckFailed",
    "check_controls",
    "license_batch",
    "preregister",
    "propose_control_claims",
]

# The two SensorKit known-answer controls (windows VERIFIED against SensorKit + the reimpl):
#   R248Q  CCG->CCA @ var_index 2  -> "engineered" (ordinal 1)  -> clears tier_bar 1  -> LICENSED
#   R248W  CCG->CUG @ var_index 1  -> "unsenseable" (ordinal 0) -> below tier_bar 1   -> withheld
_REF = "sensor::senseability:tp53-r248-controls"
# TP53 locus on GRCh38 (chr17); the R248 codon sits near 7,674,220.
_ASSEMBLY, _CHROM = "GRCh38", "chr17"


def propose_control_claims() -> list[Claim]:
    """The R248Q (positive) + R248W (negative) SensorKit known-answer controls."""
    return [
        sensor_senseability_claim(
            "sensor-R248Q", ref=_REF,
            subject=GenomicRegion(id="TP53:R248Q", display="TP53 R248Q", assembly=_ASSEMBLY,
                                  chrom=_CHROM, start=7674220, end=7674222),
            window_wt="CCG", window_mut="CCA", var_index=2, max_dist=5, mode="snv",
            tier_bar=1, name="R248Q"),
        sensor_senseability_claim(
            "sensor-R248W", ref=_REF,
            subject=GenomicRegion(id="TP53:R248W", display="TP53 R248W", assembly=_ASSEMBLY,
                                  chrom=_CHROM, start=7674220, end=7674222),
            window_wt="CCG", window_mut="CUG", var_index=1, max_dist=5, mode="snv",
            tier_bar=1, name="R248W"),
    ]


def preregister(corpus: Corpus, claims: list[Claim]) -> Corpus:
    """Admit the proposed claims into the corpus (PENDING — no standing yet). UNLIKE the e-LOND
    spine, this capability's license is the two-classifier reproduction (no e-value), so NO e-LOND
    slot is registered here — the claims are admitted through the §9 invariance precondition only
    (drops any scale-INCOHERENT claim before standing) and appended to corpus.claims."""
    claims, _refused = admit_by_invariance(claims)
    return corpus.model_copy(update={"claims": corpus.claims + tuple(claims)})


def license_batch(corpus: Corpus, claims: list[Claim]) -> Corpus:
    """Confer standing on the pre-registered controls: run the two air-gapped legs (SensorKit vs the
    independent reimplementation) + registry + oracle through run_cycle, ONE run_cycle PER CLAIM.

    Per-claim isolation (as in expression_floor_populate.license_batch): a reference_leaf criterion
    earns evidence_against_null=0.0, so with >=2 pending claims sharing one run_cycle the BH
    cardinality bar (m=2) could withhold both; isolating each to m=1 keeps all-permit, leaving the
    two-classifier agreement as the sole gate. evidence=None (no e-value route). A single
    MaterializationContext resolves the license to IndependenceTier.REPRODUCED."""
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    batch_ids = {c.id for c in claims}
    acc = corpus
    for c in claims:
        if _terminal_node(c) is None:
            continue
        solo_claims = tuple(x for x in acc.claims if x.id == c.id or x.id not in batch_ids)
        solo = acc.model_copy(update={"claims": solo_claims})
        result = run_cycle(
            solo,
            (SensorSenseabilitySensorKitAdapter(), SensorSenseabilityReimplAdapter()), base,
            adapter_registry=sensor_senseability_registry(),
            oracles=sensor_senseability_oracle_registry(),
            materializations={c.id: base},
            evidence=None,
            capability_registry=CAPABILITY_CELLS)
        updated = result.corpus.by_id().get(c.id, c)
        acc_claims = tuple(updated if x.id == c.id else x for x in acc.claims)
        acc = acc.model_copy(update={"claims": acc_claims, "fdr_ledger": result.corpus.fdr_ledger})
    return acc
