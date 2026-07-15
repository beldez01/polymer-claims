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
  * Ch6 CAR-reader landscape — CATEGORICAL (tag/maturity/IP), built here as `PropositionLeaf` reported
    claims (`ch6_car_reader_claims`); the one quantitative prior (CAR triggering ~10²–10⁴) is `synbio-c3`.
"""
from __future__ import annotations

from polymer_grammar.leaf import MeasurementContext

from .reference_materializer import materialize_reference_table, reference_proposition_claim

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


def ch6_car_reader_claims():
    """Ch6 — the CAR-T reader landscape (Track B / slide 13): effector → tag/antigen it reads, clinical
    maturity, IP/trial. Curated from `magnum-opus/part-04-actuation-surface-tags.md` + `seed-report §12`.
    Reported CONJECTURED proposition claims (categorical, not scalar); ids `ch6-<key>`. The one
    quantitative prior — CAR triggering ≈ 10²–10⁴ molecules/cell — is already `synbio-c3`."""
    src = ("supporting-research/magnum-opus/part-04-actuation-surface-tags.md",
           "OptoCART actuation landscape (curated)")

    def _r(key, title, data):
        return reference_proposition_claim(
            claim_id=f"ch6-{key}", title=title, data=data,
            warrant="literature-curated CAR-reader landscape (part-04)",
            source_ref=src[0], source_title=src[1])

    return [
        _r("anti-fitc", "anti-FITC CAR — FITC tag, IN-HUMAN (ENLIGHten-01)",
           "Reads a fluorescein (FITC) tag via an anti-FITC scFv bridged by a FITC-conjugate adaptor; "
           "strictly AND-gated on tag+antigen. Clinical: IN-HUMAN — ENLIGHten-01 Phase 1 (NCT05312411, "
           "FITC-E2 CAR + folate-fluorescein, osteosarcoma; Tamada 2012, Ahmed 2023). Prototype "
           "clinically-validated tag-reader; FITC is xenobiotic (no endogenous targets)."),
        _r("unicar", "UniCAR / La-epitope — E5B9 tag, IN-HUMAN, built-in OFF switch",
           "Reads a short La-derived peptide (E5B9) target module; antigen-agnostic. Clinical: IN-HUMAN. "
           "Fast pharmacologic OFF: cells idle until a short-half-life module is infused and auto-shut-off "
           "on clearance (Bachmann 2019). Cleanest off-the-shelf fit; the SensorKit payload registry "
           "names the UniCAR/La-epitope lead."),
        _r("supra-zipcar", "SUPRA / zipCAR — leucine-zipper tag (preclinical)",
           "Reads a leucine-zipper tag via a zipFv adaptor; combinatorial/tunable. Clinical: preclinical."),
        _r("spytag", "SpyTag/SpyCatcher — covalent tag (preclinical)",
           "Reads a SpyTag via a covalent SpyCatcher bond; irreversible pairing. Clinical: preclinical."),
        _r("biotin-bbir", "biotin-BBIR — biotin tag (preclinical)",
           "Biotin-binding immune receptor reads biotinylated adaptors. Clinical: preclinical."),
        _r("conventional", "Conventional CARs (CD19/CD20/BCMA/CD33/CD123/GD2) — native antigen, most mature",
           "Read a native surface antigen directly; MOST clinically mature but antigen-SPECIFIC — the "
           "payload must display that native ectodomain as a mini-antigen, not a swappable tag."),
    ]


def ch5_burden_claims():
    """Ch5 — disease burden. Real SEER Cancer Stat Facts figures FETCHED 2026-07-15 (age-adjusted
    incidence per 100k/yr, 2019–2023; 5-yr relative survival 2016–2022) for the two candidate-universe
    cancers in SEER: AML and pancreatic (PDAC). Two-stratum CONJECTURED reported claims; ids `ch5-<key>`.

    GAP (flagged, NOT fabricated): MPN (PV/ET/PMF — JAK2/CALR), CHIP (ASXL1), and EBV+ PTLD are not in
    SEER stat-facts pages and need targeted registry/literature sources; left unmaterialized here."""
    seer = "SEER Cancer Stat Facts (seer.cancer.gov; incidence 2019–2023, survival 2016–2022)"
    rows = [
        dict(key="aml-incidence", title="AML age-adjusted incidence ≈ 4.4 / 100k / yr (SEER)",
             value=4.4, formula="age_adjusted_new_cases_per_100k_per_year",
             context=MeasurementContext(condition="acute myeloid leukemia"),
             source_ref="SEER Cancer Stat Facts: AML (seer.cancer.gov/statfacts/html/amyl.html, 2019–2023)",
             source_title=seer),
        dict(key="aml-survival", title="AML 5-yr relative survival ≈ 33.4% (SEER)",
             value=0.334, formula="five_year_relative_survival",
             context=MeasurementContext(condition="acute myeloid leukemia"),
             source_ref="SEER Cancer Stat Facts: AML (seer.cancer.gov/statfacts/html/amyl.html, 2016–2022)",
             source_title=seer),
        dict(key="pdac-incidence", title="Pancreatic cancer age-adjusted incidence ≈ 13.9 / 100k / yr (SEER)",
             value=13.9, formula="age_adjusted_new_cases_per_100k_per_year",
             context=MeasurementContext(condition="pancreatic cancer"),
             source_ref="SEER Cancer Stat Facts: Pancreas (seer.cancer.gov/statfacts/html/pancreas.html, 2019–2023)",
             source_title=seer),
        dict(key="pdac-survival", title="Pancreatic cancer 5-yr relative survival ≈ 13.7% (SEER)",
             value=0.137, formula="five_year_relative_survival",
             context=MeasurementContext(condition="pancreatic cancer"),
             source_ref="SEER Cancer Stat Facts: Pancreas (seer.cancer.gov/statfacts/html/pancreas.html, 2016–2022)",
             source_title=seer),
    ]
    return materialize_reference_table(rows, id_prefix="ch5")


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
