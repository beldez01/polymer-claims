"""F3 — the reference-table → claim materializer (ADAPTER-DATA-CHANNELS Ch4-Ch7).

A reported reference value (recurrence, disease burden, a CAR-T reader threshold, a biophysical
prior) becomes an engine claim through this schema layer: each row emits a `Status.CONJECTURED`
claim with `GenerationMode.LITERATURE_EXTRACTED` provenance — the TWO-STRATUM discipline, so it
never self-licenses and is warrant-capped and defeasible. This is the `synbio/claims.py` factory
pattern generalized so a whole table materializes at once, rather than hand-writing each claim.

It is NOT `attested_ingest` (which resolves an ALREADY-EXISTING claim with an external verdict and
appends a ResolutionKind.ATTESTED record). Materialize first here; attest later if desired.

Umbrella-side; reuses the pure-grammar `reported_quantity@v1` pattern. NEVER fabricates — every value
must come from a supplied row/source; the real Ch4/Ch5/Ch6 tables are operator-curated data.
"""
from __future__ import annotations

from collections.abc import Iterable

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, MeasurementContext, PropositionLeaf, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.provenance import GenerationMode, Provenance
from polymer_grammar.status import Status

# Registered in the pure grammar (pattern.py) — the analysis-class reported patterns.
REPORTED_QUANTITY = PatternRef(id="reported_quantity", version="v1")
REPORTED_PROPOSITION = PatternRef(id="mechanistic_law", version="v1")   # the proposition-carrying pattern


def reference_quantity_claim(
    *, claim_id: str, title: str, value: float, source_ref: str, source_title: str,
    unit: str | None = None, formula: str | None = None, uncertainty: float | None = None,
    low: float | None = None, high: float | None = None,
    measurement_basis: MeasurementBasis = MeasurementBasis.DERIVED,
    context: MeasurementContext | None = None, subject=None,
) -> Claim:
    """One reported reference value as a CONJECTURED (two-stratum) claim: LITERATURE_EXTRACTED,
    warrant-capped, never self-licensing. `source_ref`/`source_title` record the citation."""
    leaf = QuantityLeaf(
        value=float(value), unit=unit, formula=formula, uncertainty=uncertainty,
        low=low, high=high, measurement_basis=measurement_basis, context=context,
    )
    return Claim(
        id=claim_id, title=title, pattern=REPORTED_QUANTITY, leaves=(leaf,),
        status=Status.CONJECTURED, subject=subject,
        provenance=Provenance(
            generated_by=GenerationMode.LITERATURE_EXTRACTED,
            method=source_ref, version=source_title, search_cardinality=1,
        ),
    )


def reference_proposition_claim(
    *, claim_id: str, title: str, data: str, warrant: str, source_ref: str, source_title: str,
    subject=None,
) -> Claim:
    """A reported CATEGORICAL/qualitative reference fact (e.g. a CAR-reader landscape entry) as a
    CONJECTURED two-stratum claim carrying a `PropositionLeaf` — warrant-capped, defeasible, never
    self-licensing. For reference values that are not scalar quantities."""
    leaf = PropositionLeaf(data=data, warrant=warrant, warrant_type="expert_judgment")
    return Claim(
        id=claim_id, title=title, pattern=REPORTED_PROPOSITION, leaves=(leaf,),
        status=Status.CONJECTURED, subject=subject,
        provenance=Provenance(
            generated_by=GenerationMode.LITERATURE_EXTRACTED,
            method=source_ref, version=source_title, search_cardinality=1,
        ),
    )


def materialize_reference_table(rows: Iterable[dict], *, id_prefix: str) -> list[Claim]:
    """Map a reference table (rows of `reference_quantity_claim` kwargs, each with a `key`) to
    CONJECTURED reference claims. The claim id is ``<id_prefix>-<key>``. Never fabricates — every
    field comes from the row; a row missing a required field raises (honest failure)."""
    out: list[Claim] = []
    for r in rows:
        row = dict(r)
        key = row.pop("key")
        out.append(reference_quantity_claim(claim_id=f"{id_prefix}-{key}", **row))
    return out


def ch7_biophysical_prior_claims() -> list[Claim]:
    """Ch7 remainder — the biophysical priors the interaction model needs that are NOT yet ingested
    (BRET R₀, the interaction-model dynamic-range span). Values are the operator's own stated figures
    from `SCREEN-INTERACTION-PLAN.md` §5.2/§5.3 — the plan is the cited source, not a fabrication.
    (The ADAR/CAR priors already exist as synbio-c1..c4.)"""
    src = ("SCREEN-INTERACTION-PLAN.md §5.2-5.3", "Polymer Biologics / OptoCART interaction model")
    return materialize_reference_table(
        [
            dict(key="bret-r0", title="BRET Förster radius R₀ ≈ 4–5 nm (NanoLuc opto-CAR pair)",
                 value=4.5, low=4.0, high=5.0, unit="nm",
                 measurement_basis=MeasurementBasis.FUNDAMENTAL,
                 source_ref=src[0], source_title=src[1]),
            dict(key="sensor-dynamic-range", title="Sensor dynamic range span ≈ 100–800× (edited/unedited)",
                 value=450.0, low=100.0, high=800.0, formula="edited_payload / unedited_payload",
                 measurement_basis=MeasurementBasis.DERIVED,
                 source_ref=src[0], source_title=src[1]),
        ],
        id_prefix="ch7",
    )
