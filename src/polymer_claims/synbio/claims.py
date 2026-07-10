"""The five probe claims — reported constraints from the treatise, formalized through the
real v1.3 grammar (Phase 0 spec §2, §6).

Every claim here is REPORTED (`GenerationMode.LITERATURE_EXTRACTED`) and therefore
`Status.CONJECTURED`: a licensed status requires a two-leg recompute (Phase 2), which the
probe deliberately does not do. The point is to measure formalization yield and flush IR
gaps, not to license.

GAP (logged): a bare reported quantity has no home pattern in `pattern.registry` (which only
carries `adjusted_effect@v1`). We reference a placeholder `PatternRef("reported_quantity",
"v1")` — structurally valid because `Claim.pattern` is an unresolved id+version, not a
registry lookup — and record the missing pattern as an analysis-class expansion (Task 6).
"""
from __future__ import annotations

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.provenance import GenerationMode, Provenance
from polymer_grammar.status import Status

from .sources import SOURCES

# Placeholder pattern for reported point-quantities (see module GAP note).
_REPORTED_QUANTITY = PatternRef(id="reported_quantity", version="v1")


def _reported_provenance(source_key: str) -> Provenance:
    """Provenance for a reported literature fact: LITERATURE_EXTRACTED, one hypothesis."""
    src = SOURCES[source_key]
    return Provenance(
        generated_by=GenerationMode.LITERATURE_EXTRACTED,
        method=src.ref,
        version=src.title,
        search_cardinality=1,
    )


def mismatch_energy_claim() -> Claim:
    """C1 — a single Watson-Crick mismatch discriminates by ~2 kcal/mol (range 1-3) against
    kT ≈ 0.62 kcal/mol at 310 K. A FUNDAMENTAL quantity (energy, ratio-scale, UCUM unit)."""
    return Claim(
        id="synbio-c1-mismatch-energy",
        title="Single Watson-Crick mismatch discrimination energy ≈ 2 kcal/mol at 310 K",
        pattern=_REPORTED_QUANTITY,
        leaves=(
            QuantityLeaf(
                value=2.0,
                unit="kcal/mol",
                uncertainty=1.0,
                measurement_basis=MeasurementBasis.FUNDAMENTAL,
            ),
        ),
        status=Status.CONJECTURED,
        provenance=_reported_provenance("PLM-I"),
    )
