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
