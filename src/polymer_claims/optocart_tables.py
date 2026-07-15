"""OptoCART F3 reference tables (Ch4 recurrence) — materialized from the curated research prose.

Values are extracted from the operator's own cited docs (`Polymer Biologics/supporting-research/`:
`CANDIDATE-RESCREEN-2026-06.md`, `magnum-opus/part-08-indications.md`) — the two-stratum ATTESTED
pattern: each recurrence figure enters as a `Status.CONJECTURED` reported claim (warrant-capped,
defeasible) via `reference_materializer`, with the source doc + primary citation recorded. NOT
measured here; a materializer, not a gate.

Scope (honest):
  * Ch4 recurrence — quantitative fractions, well-covered → built here.
  * Ch5 burden — mostly qualitative unmet-need in the prose; hard incidence/prevalence (per 100k)
    is NOT on disk → a SEER/GLOBOCAN lookup, not materializable from the docs.
  * Ch6 CAR-reader landscape — mostly CATEGORICAL (tag/maturity/IP); the one quantitative prior
    (CAR triggering ~10²–10⁴) is already `synbio-c3`. The landscape table is reference metadata, not
    a quantity claim.
"""
from __future__ import annotations

from polymer_grammar.leaf import MeasurementContext

from .reference_materializer import materialize_reference_table

# Source shorthand: the curated screen docs (which themselves cite the primary literature).
_RESCREEN = "supporting-research/CANDIDATE-RESCREEN-2026-06.md"
_IND = "supporting-research/magnum-opus/part-08-indications.md"
_TITLE = "OptoCART candidate screen (curated)"


def _row(key, title, value, disease, source_ref, *, low=None, high=None):
    return dict(
        key=key, title=title, value=value, low=low, high=high,
        formula=f"fraction_of_{disease.replace(' ', '_')}_cases",
        context=MeasurementContext(condition=disease),
        source_ref=source_ref, source_title=_TITLE,
    )


def ch4_recurrence_claims():
    """Ch4 — recurrence fractions for the candidate universe (feature → fraction of a disease's
    cases). Values from CANDIDATE-RESCREEN + part-08 (primary cites in those docs). One reported
    CONJECTURED claim per feature; ids `ch4-<key>`."""
    return materialize_reference_table(
        [
            _row("asxl1-dupg", "ASXL1 c.1934dupG (p.G646Wfs*12) ≈ 40% of ASXL1-CHIP mutations",
                 0.40, "ASXL1 CHIP", _RESCREEN),
            _row("npm1-typea", "NPM1 type-A ≈ 30–35% of adult AML", 0.325, "adult AML",
                 _IND, low=0.30, high=0.35),
            _row("flt3-itd", "FLT3-ITD ≈ 30% of NPMc+ AML", 0.30, "NPMc+ AML", _IND),
            _row("calr-type1", "CALR type-1 (52-bp del) ≈ 53% of CALR-mutant MPN", 0.53,
                 "CALR-mutant MPN", _IND),
            _row("calr-type2", "CALR type-2 (5-bp ins) ≈ 32% of CALR-mutant MPN", 0.32,
                 "CALR-mutant MPN", _IND),
            _row("jak2-v617f-pv", "JAK2 V617F ≈ 95% of polycythemia vera", 0.95,
                 "polycythemia vera", _IND),
            _row("jak2-v617f-etpmf", "JAK2 V617F ≈ 50–60% of ET/PMF", 0.55, "ET or PMF",
                 _IND, low=0.50, high=0.60),
            _row("kras-g12d", "KRAS G12D ≈ 39% of KRAS-mutant PDAC", 0.39, "KRAS-mutant PDAC", _IND),
            _row("kras-g12v", "KRAS G12V ≈ 32% of KRAS-mutant PDAC", 0.32, "KRAS-mutant PDAC", _IND),
            _row("tp53-r175h", "TP53 R175H ≈ 7–8% of TP53-mutant tumors", 0.075,
                 "TP53-mutant tumors", _IND, low=0.07, high=0.08),
        ],
        id_prefix="ch4",
    )
