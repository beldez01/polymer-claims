"""te_family_windows: parameterized rmsk subfamily selection (generalizes hervk_ltr5_windows)."""
from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from polymer_claims.ingest.te_loci import te_family_windows

# rmsk columns 0..12: bin swScore milliDiv milliDel milliIns genoName genoStart genoEnd
# genoLeft strand repName repClass repFamily
_ROWS = [
    ("0", "1", "0", "0", "0", "chr1", "100", "600", "-1", "+", "L1HS", "LINE", "L1"),
    ("0", "1", "0", "0", "0", "chr2", "5000", "5500", "-1", "-", "L1HS", "LINE", "L1"),
    ("0", "1", "0", "0", "0", "chr1", "200", "700", "-1", "+", "AluYa5", "SINE", "Alu"),
    ("0", "1", "0", "0", "0", "chr1", "9", "50", "-1", "+", "LTR5_Hs", "LTR", "ERVK"),
    # non-standard chromosome must be dropped
    ("0", "1", "0", "0", "0", "chr1_KI270713v1_random", "1", "9", "-1", "+", "L1HS", "LINE", "L1"),
]


def _write_rmsk(path: Path, gz: bool = False) -> Path:
    text = "".join("\t".join(r) + "\n" for r in _ROWS)
    if gz:
        with gzip.open(path, "wt") as fh:
            fh.write(text)
    else:
        path.write_text(text)
    return path


def test_selects_by_rep_name_only(tmp_path):
    rmsk = _write_rmsk(tmp_path / "rmsk.txt")
    w = te_family_windows(rmsk, rep_name="L1HS")
    # two L1HS on std chroms; the _random contig row dropped
    assert w == [("chr1", 100, 600), ("chr2", 5000, 5500)]


def test_conjunctive_name_and_class(tmp_path):
    rmsk = _write_rmsk(tmp_path / "rmsk.txt")
    # class mismatch => no rows (L1HS is LINE, not LTR)
    assert te_family_windows(rmsk, rep_name="L1HS", rep_class="LTR") == []
    assert te_family_windows(rmsk, rep_name="LTR5_Hs", rep_class="LTR") == [("chr1", 9, 50)]


def test_family_filter(tmp_path):
    rmsk = _write_rmsk(tmp_path / "rmsk.txt")
    assert te_family_windows(rmsk, rep_family="Alu") == [("chr1", 200, 700)]


def test_dropped_nonstandard_chrom(tmp_path):
    rmsk = _write_rmsk(tmp_path / "rmsk.txt")
    w = te_family_windows(rmsk, rep_name="L1HS")
    assert all(not chrom.endswith("_random") for chrom, _, _ in w)


def test_gzip_input(tmp_path):
    rmsk = _write_rmsk(tmp_path / "rmsk.txt.gz", gz=True)
    assert te_family_windows(rmsk, rep_name="AluYa5") == [("chr1", 200, 700)]


def test_requires_at_least_one_predicate(tmp_path):
    rmsk = _write_rmsk(tmp_path / "rmsk.txt")
    with pytest.raises(ValueError):
        te_family_windows(rmsk)


def test_matches_hervk_selector(tmp_path):
    """Parameterized selector must reproduce the hard-coded HERV-K one exactly."""
    from polymer_claims.ingest.hervk_loci import hervk_ltr5_windows

    rmsk = _write_rmsk(tmp_path / "rmsk.txt")
    assert te_family_windows(rmsk, rep_name="LTR5_Hs", rep_class="LTR") == hervk_ltr5_windows(rmsk)


def test_random_background_windows_deterministic_and_in_bounds():
    from polymer_claims.ingest.te_loci import _HG38_STD_SIZES, random_background_windows

    a = random_background_windows(200, 500, seed=7)
    b = random_background_windows(200, 500, seed=7)
    c = random_background_windows(200, 500, seed=8)
    assert a == b            # deterministic given seed
    assert a != c            # different seed -> different draw
    assert len(a) == 200
    assert a == sorted(a)    # sorted
    for chrom, start, end in a:
        assert end - start == 500
        assert 0 <= start and end <= _HG38_STD_SIZES[chrom]   # in-bounds
