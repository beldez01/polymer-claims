"""Expression two-leg spine SEAM (Phase 2d foundation) — the machinery for a future LICENSED
synbio claim, exercised on synthetic values only. NO real data is pinned this session and
`run_cycle` is NOT invoked, so NOTHING here licenses (status stays CONJECTURED).

DATA GATE (next session): pin real AML fusion-expression RNA-seq into data/ (Option A:
TCGA-LAML RNA-seq TPM from UCSC Xena -> "RUNX1-RUNX1T1 clears the ~13 TPM floor in AML";
Option B, self-contained: BLUEPRINT hematopoietic RSEM -> "RUNX1T1/ETO silent in normal
blood"). Then two independent estimators feed `two_leg_floor_agreement` through the
SE-Contract seam + the two-leg AdapterRegistry, and run_cycle mints the license.
"""
from __future__ import annotations

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import (
    MeasurementBasis,
    MeasurementContext,
    QuantityLeaf,
)
from polymer_grammar.provenance import GenerationMode, Provenance
from polymer_grammar.status import Status

from .patterns import REPORTED_QUANTITY


def expression_floor_claim(gene: str, tissue: str, floor_tpm: float) -> Claim:
    return Claim(
        id=f"synbio-spine-{gene.lower()}-{tissue.lower()}-tpm-floor",
        title=f"{gene} clears the ~{floor_tpm:g} TPM expression floor in {tissue}",
        pattern=REPORTED_QUANTITY,
        leaves=(
            QuantityLeaf(
                value=floor_tpm,
                unit=None,
                uncertainty=None,
                measurement_basis=MeasurementBasis.DERIVED,
                formula="gene_tpm >= floor_tpm",
                context=MeasurementContext(tissue=tissue, assay="RNA-seq TPM"),
            ),
        ),
        status=Status.CONJECTURED,  # scaffold: no recompute, no license
        provenance=Provenance(
            generated_by=GenerationMode.LITERATURE_EXTRACTED,
            method="synbio.spine (seam scaffold — data-gated)",
            version="v0",
            search_cardinality=1,
        ),
    )


def two_leg_floor_agreement(tpm_leg_a: float, tpm_leg_b: float, floor: float) -> bool:
    """Both independent legs must agree the value clears the floor (the two-leg gate's
    agreement predicate). Exercised on synthetic values; the real legs arrive with data."""
    return tpm_leg_a >= floor and tpm_leg_b >= floor
