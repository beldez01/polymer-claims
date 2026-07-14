"""Measurement-space registry (B1) — one catalog, two consumers.

Behavior tests per specs/2026-07-14-measurement-space-registry-design.md §4.
Umbrella-side; no grammar/protocol/Corpus change.
"""
from __future__ import annotations

from pathlib import Path


from polymer_claims.contracts import using_contract_root
from polymer_claims.measurement_space import (
    MeasurementSpace,
    Modality,
    ScaleType,
    all_spaces,
    available_spaces,
    coverage,
    get_space,
    resolve_space,
    spaces_for_contract,
    spaces_for_modality,
)

# space_ids expected for the real committed contracts (§2.2)
_EXPECTED = {
    "gdsc_pharmaco@1::meth",
    "gdsc_pharmaco@1::auc",
    "gdsc_pharmaco_promoter@1::meth",
    "gdsc_pharmaco_promoter@1::auc",
    "tcga_laml_fusion_expr@1::expr",
    "target_aml_fusion_expr@1::expr",
    "tcga_laml_cbf_expr@1::expr",
    "target_aml_cbf_expr@1::expr",
    "tcga_laml_idh@2::cg",
}


def test_catalog_completeness_unique_and_sorted():
    spaces = all_spaces()
    ids = [s.space_id for s in spaces]
    assert set(ids) >= _EXPECTED
    assert len(ids) == len(set(ids)), "space_ids must be unique"
    assert ids == sorted(ids), "all_spaces() must be deterministically sorted by space_id"


def test_every_entry_declares_scale_type_and_invariance_group():
    # The measurement-foundation definition-of-done: every space declares BOTH.
    for s in all_spaces():
        assert isinstance(s, MeasurementSpace)
        assert isinstance(s.scale_type, ScaleType), s.space_id
        assert isinstance(s.modality, Modality), s.space_id
        assert isinstance(s.invariance_group, str) and s.invariance_group.strip(), s.space_id


def test_get_space_roundtrips_and_missing_is_none():
    assert get_space("gdsc_pharmaco_promoter@1::meth").modality is Modality.METHYLATION_PROMOTER
    assert get_space("does_not_exist@9::nope") is None


def test_modality_split_disjoint_and_nonempty():
    gene = {s.space_id for s in spaces_for_modality(Modality.METHYLATION_GENEBODY)}
    prom = {s.space_id for s in spaces_for_modality(Modality.METHYLATION_PROMOTER)}
    assert gene and prom
    assert gene.isdisjoint(prom)
    assert "gdsc_pharmaco@1::meth" in gene
    assert "gdsc_pharmaco_promoter@1::meth" in prom


def test_spaces_for_contract():
    ids = {s.space_id for s in spaces_for_contract("gdsc_pharmaco@1")}
    assert ids == {"gdsc_pharmaco@1::meth", "gdsc_pharmaco@1::auc"}


def test_available_uses_real_load_contract():
    # With the bundled contract root, the committed contracts resolve -> available.
    avail = {s.space_id for s in available_spaces()}
    assert "gdsc_pharmaco@1::meth" in avail
    assert _EXPECTED <= avail  # every catalog contract has committed json+tsv


def test_resolve_grounds_to_promoter():
    s = resolve_space(Modality.METHYLATION_PROMOTER)
    assert s is not None
    assert s.space_id == "gdsc_pharmaco_promoter@1::meth"


def test_resolve_no_fabrication_when_no_contract_available(tmp_path: Path):
    # Empty contract root: nothing resolves -> availability empty -> resolve returns None,
    # never fabricates a space with no data behind it (de Bruijn grounding).
    with using_contract_root(tmp_path):
        assert available_spaces() == ()
        assert resolve_space(Modality.METHYLATION_PROMOTER) is None


def test_resolve_excludes_origin_space():
    # The evaluator must not re-propose the space it is re-parameterizing away from.
    # promoter meth is the only promoter space -> excluding it yields None.
    s = resolve_space(
        Modality.METHYLATION_PROMOTER,
        exclude_space_id="gdsc_pharmaco_promoter@1::meth",
    )
    assert s is None


def test_resolve_deterministic_first_when_multiple_match():
    # EXPRESSION_TPM has several spaces; resolve returns the first available by sorted space_id.
    s = resolve_space(Modality.EXPRESSION_TPM)
    assert s is not None
    candidates = sorted(
        x.space_id for x in spaces_for_modality(Modality.EXPRESSION_TPM)
    )
    assert s.space_id == candidates[0]


def test_coverage_groups_by_modality_and_scale():
    cov = coverage()
    # methylation_genebody is a ratio-scale beta space present in the catalog
    key = (Modality.METHYLATION_GENEBODY, ScaleType.RATIO)
    assert key in cov
    assert "gdsc_pharmaco@1::meth" in cov[key]
