"""TE multi-contrast CAMPAIGN driver (te_campaign.run_te_campaign).

Synthetic, no real data. Verifies the extract-ONCE / run-many-contrasts orchestration:
  * both gates (n-DMP + background-enrichment) run per contrast with their own e-LOND ledgers,
  * a contrast on a DIFFERENT grouping column (cell_type_broad) works off the same extraction,
  * a contrast whose levels are absent is SKIPPED (not crashed),
  * claim ids are contrast-prefixed so contrasts never collide.
The REAL drive is scripts/rip_te_campaign.py.
"""
from __future__ import annotations

import gzip

from polymer_grammar import Status

from polymer_claims.te_ndmp import TeFamilySpec


def _write_bed(path, rows):
    with gzip.open(path, "wt") as fh:
        fh.write("#chr\tstart\tend\tbeta\ttotal_cov\ttotal_meth\tn_cpgs\n")
        for chrom, pos, beta, cov in rows:
            fh.write(f"{chrom}\t{pos}\t{pos+1}\t{beta:.4f}\t{cov}\t{round(beta*cov)}\t1\n")


def _manifest(path, entries):
    lines = ["gsm_accession\tfilename_stem\tcell_type\tcell_type_broad\tlineage\treplicates"]
    for stem, ctb, lineage in entries:
        lines.append(f"G{stem}\t{stem}\t{ctb}_ct\t{ctb}\t{lineage}\t1")
    path.write_text("\n".join(lines) + "\n")


# chrom -> (n_sep, n_flat): chr2 FAMA fully separates; chr3 FAMB flat; chr4 BG is 3/10 separating (~0.3).
_LAYOUT = {"chr2": (12, 0), "chr3": (0, 12), "chr4": (3, 7)}
_FAM_WIN = {"fama": [("chr2", 500, 9000)], "famb": [("chr3", 500, 9000)]}
_BG_WIN = [("chr4", 500, 9000)]


def _atlas(tmp_path, *, n_per_group=5):
    bed = tmp_path / "bed"
    bed.mkdir()

    def w(stem, s_idx, lineage):
        rows = []
        for chrom, (n_sep, n_flat) in _LAYOUT.items():
            for i in range(n_sep + n_flat):
                pos = 1000 + 10 * i
                base = (0.90 if lineage == "Lymphoid" else 0.10) if i < n_sep else 0.50
                rows.append((chrom, pos, min(0.99, max(0.01, base + 0.003 * s_idx)), 20))
        _write_bed(bed / f"{stem}.hg38.bed.gz", rows)

    entries = []
    for i in range(n_per_group):
        w(f"Ly{i}", i, "Lymphoid")
        w(f"My{i}", i, "Myeloid")
        entries += [(f"Ly{i}", "T_cell", "Lymphoid"), (f"My{i}", "Monocyte", "Myeloid")]
    man = tmp_path / "m.tsv"
    _manifest(man, entries)
    return bed, man


_PANEL = (
    TeFamilySpec("fama", "FAMA", "LTR", "FAMA separating", "synthetic"),
    TeFamilySpec("famb", "FAMB", "LTR", "FAMB flat", "synthetic"),
)


def _patch(monkeypatch):
    import polymer_claims.te_campaign as camp
    monkeypatch.setattr(camp, "te_family_windows_multi",
                        lambda _p, specs: {key: _FAM_WIN[key] for key, _rn, _rc in specs})
    monkeypatch.setattr(camp, "random_background_windows", lambda n, size, seed: _BG_WIN)


def test_campaign_runs_both_gates_across_contrasts_and_skips_absent(tmp_path, monkeypatch):
    from polymer_claims.te_campaign import Contrast, run_te_campaign
    _patch(monkeypatch)
    bed, man = _atlas(tmp_path)

    contrasts = (
        Contrast("linLvM", "lineage", "Lymphoid", "Myeloid", "baseline"),
        Contrast("tcellVmono", "cell_type_broad", "T_cell", "Monocyte", "group_col flexibility"),
        Contrast("absent", "cell_type_broad", "B_cell", "NK", "no such samples -> skip"),
    )
    res = run_te_campaign(
        "unused_rmsk", bed, man, tmp_path / "contracts",
        contrasts=contrasts, panel=_PANEL, bg_reps=2, alpha=0.05, min_cov=4)

    by_key = {c.contrast.key: c for c in res.contrasts}
    assert set(by_key) == {"linLvM", "tcellVmono", "absent"}

    # absent contrast: skipped, no claims
    assert by_key["absent"].skipped and not by_key["absent"].ndmp

    for key in ("linLvM", "tcellVmono"):
        cr = by_key[key]
        assert cr.skipped is None
        assert abs(cr.bg_rate_ttest - 0.3) < 0.05 and abs(cr.bg_rate_rank - 0.3) < 0.05  # 3/10 bg
        nd = {v.key: v for v in cr.ndmp}
        # FAMA fully separates -> n-DMP LICENSED (beyond chance); FAMB flat -> not licensed.
        assert nd["fama"].status == Status.LICENSED and nd["fama"].count_ttest == 12
        assert nd["famb"].status != Status.LICENSED and nd["famb"].count_ttest == 0
        en = {v.key: v for v in cr.enrichment}
        # FAMA rate 1.0 >> 0.3 background -> ENRICHED (fold ~3.3, both legs) -> LICENSED.
        assert en["fama"].fold_ttest > 1.0 and en["fama"].status == Status.LICENSED
        # FAMB rate 0 < background -> not enriched.
        assert en["famb"].status != Status.LICENSED

    # contrast-prefixed, collision-free claim ids across the two live contrasts
    ids = {v.key + "|" + c.contrast.key
           for c in res.contrasts if not c.skipped for v in c.ndmp}
    assert len(ids) == 4  # 2 families x 2 contrasts, all distinct
