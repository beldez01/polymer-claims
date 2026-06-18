from __future__ import annotations

from polymer_claims.assets import methylation_asset_catalog


def test_methylation_asset_catalog_includes_bundled_fixtures():
    assets = methylation_asset_catalog()
    refs = {a.ref for a in assets}
    assert "se:epicv2_casectrl_demo@1" in refs
    assert "se:epicv2_casectrl_powered@1" in refs
    assert all(a.group_col == "Sample_Group" for a in assets)
    assert all(a.operations for a in assets)


def test_methylation_asset_catalog_can_list_missing_local_assets():
    assets = methylation_asset_catalog(include_missing_local=True)
    refs = {a.ref for a in assets}
    assert "se:tcga_laml_idh@1" in refs
    assert "se:tcga_laml_idh_test@1" in refs
