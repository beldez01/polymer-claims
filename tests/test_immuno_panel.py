from pathlib import Path
import pytest
from polymer_claims.panels import load_panel, LocusSpec, assert_rmsk_hg38

PANEL = Path("src/polymer_claims/panels/immuno_meth_v1.tsv")


def test_panel_parses_in_order_with_frozen_fields():
    panel = load_panel(PANEL)
    assert len(panel) >= 8
    first = panel[0]
    assert isinstance(first, LocusSpec)
    assert first.klass in {"HLA", "TE"}
    assert first.tau == pytest.approx(0.10)
    assert first.comparator in {"GT", "LT"}
    # order is load-bearing (e-LOND): the parsed order equals the file order
    ids_file = [ln.split("\t")[0] for ln in PANEL.read_text().splitlines()[1:] if ln.strip()]
    assert [l.locus_id for l in panel] == ids_file


def test_rmsk_build_guard_rejects_non_hg38(tmp_path):
    fake = tmp_path / "rmsk.txt"
    # an hg19-style chr1 end (249,250,621) must be rejected
    fake.write_text("585\t0\t0\t0\tchr1\t10000\t249250621\t...\n")
    with pytest.raises(ValueError):
        assert_rmsk_hg38(fake)


def test_group_col_defaults_to_cell_type_broad_when_absent():
    panel = load_panel(PANEL)  # immuno_meth_v1.tsv has no group_col column
    assert panel
    assert all(loc.group_col == "cell_type_broad" for loc in panel)


def test_group_col_parses_when_present(tmp_path):
    panel_path = tmp_path / "lineage_panel.tsv"
    panel_path.write_text(
        "locus_id\tklass\tchrom\tstart\tend\tgroup_col\tgroup_a\tgroup_b\tcomparator\ttau\trationale\n"
        "test_locus\tHLA\tchr6\t100\t200\tlineage\tLymphoid\tMyeloid\tGT\t0.10\ttest\n"
    )
    panel = load_panel(panel_path)
    assert len(panel) == 1
    assert panel[0].group_col == "lineage"
    assert panel[0].group_a == "Lymphoid"
    assert panel[0].group_b == "Myeloid"
