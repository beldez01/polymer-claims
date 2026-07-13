"""TE-family BACKGROUND-ENRICHMENT sweep (te_enrichment.run_te_enrichment_sweep).

Synthetic, no real data. The honest recast of the n-DMP sweep: a family licenses only if its per-probe
lineage-DMP rate clears the MATCHED-BACKGROUND rate on both legs (fold>=1) AND the count e-value
(p0=background) clears the e-LOND bar. Two families through ONE shared ledger:
  * FAMA — every probe separates (rate 1.0) -> ENRICHED above the 0.5 background -> LICENSED.
  * FAMB — 4/12 probes separate (rate 0.33): it HAS real DMPs (would license under the n-DMP chance
    null), but sits BELOW the 0.5 background -> NOT licensed. This is the whole point of the pattern:
    "differentially methylated beyond chance" != "enriched above a matched background."
The REAL drive is scripts/rip_te_enrichment.py.
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
    for stem, lineage in entries:
        lines.append(f"G{stem}\t{stem}\t{lineage}_ct\t{lineage}_broad\t{lineage}\t1")
    path.write_text("\n".join(lines) + "\n")


# family key -> (chrom, n_sep, n_flat): first n_sep probes separate Lymphoid~0.9/Myeloid~0.1 (a DMP on
# both legs), the next n_flat are flat ~0.5 in both lineages (never a DMP). So the family's DMP rate is
# exactly n_sep/(n_sep+n_flat).
_LAYOUT = {"fama": ("chr2", 12, 0), "famb": ("chr3", 4, 8)}
_WINMAP = {"FAMA": [("chr2", 500, 9000)], "FAMB": [("chr3", 500, 9000)]}


def _atlas(tmp_path, *, n_per_group=5):
    bed = tmp_path / "bed"
    bed.mkdir()

    def w(stem, s_idx, lineage):
        rows = []
        for chrom, n_sep, n_flat in _LAYOUT.values():
            for i in range(n_sep + n_flat):
                pos = 1000 + 10 * i
                base = (0.90 if lineage == "Lymphoid" else 0.10) if i < n_sep else 0.50
                beta = min(0.99, max(0.01, base + 0.003 * s_idx))  # per-sample jitter -> nonzero var
                rows.append((chrom, pos, beta, 20))
        _write_bed(bed / f"{stem}.hg38.bed.gz", rows)

    entries = []
    for i in range(n_per_group):
        w(f"Ly{i}", i, "Lymphoid")
        w(f"My{i}", i, "Myeloid")
        entries += [(f"Ly{i}", "Lymphoid"), (f"My{i}", "Myeloid")]
    man = tmp_path / "m.tsv"
    _manifest(man, entries)
    return bed, man


_TEST_PANEL = (
    TeFamilySpec("fama", "FAMA", "LTR", "FAMA fully-separating family", "synthetic: rate 1.0"),
    TeFamilySpec("famb", "FAMB", "LTR", "FAMB partly-separating family", "synthetic: rate 0.33 < bg"),
)


def test_estimate_background_dmp_rates(tmp_path):
    """The background rate = per-probe DMP fraction over supplied random windows. A window over the
    fully-separating chrom yields ~1.0; over the flat chrom ~0.0."""
    from polymer_claims.te_enrichment import estimate_background_dmp_rates
    bed, man = _atlas(tmp_path)
    # chr2 = 12/12 separating -> rate 1.0; chr3 = 4/12 separating -> rate 0.333 (fraction = DMPs/probes).
    t_sep, r_sep = estimate_background_dmp_rates(
        bed, man, tmp_path / "bgc_sep", windows_by_rep={"bg0": [("chr2", 500, 9000)]})
    assert t_sep > 0.99 and r_sep > 0.99                 # every separating probe is a DMP
    t_mix, r_mix = estimate_background_dmp_rates(
        bed, man, tmp_path / "bgc_mix", windows_by_rep={"bg0": [("chr3", 500, 9000)]})
    assert abs(t_mix - 4 / 12) < 1e-9 and abs(r_mix - 4 / 12) < 1e-9   # 4 of 12 probes are DMPs


def test_sweep_licenses_enriched_family_and_rejects_below_background(tmp_path, monkeypatch):
    from polymer_claims.te_enrichment import run_te_enrichment_sweep
    import polymer_claims.te_enrichment as drv
    bed, man = _atlas(tmp_path, n_per_group=5)
    monkeypatch.setattr(drv, "te_family_windows_multi",
                        lambda _p, specs: {key: _WINMAP[rn] for key, rn, _rc in specs})

    res = run_te_enrichment_sweep(
        "unused_rmsk", bed, man, tmp_path / "contracts",
        bg_rate_ttest=0.50, bg_rate_rank=0.50,     # pre-registered matched-background rates
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4, panel=_TEST_PANEL,
    )
    by_key = {f.key: f for f in res.families}

    fama = by_key["fama"]
    assert fama.n_probes == 12 and fama.count_ttest == 12   # every probe a DMP
    assert abs(fama.fold_ttest - 12 / (0.50 * 12)) < 1e-9   # 2.0x enriched
    assert fama.status == Status.LICENSED and fama.verdict == "LICENSED"
    assert fama.e_value is not None and fama.bar is not None and fama.e_value >= fama.bar

    famb = by_key["famb"]
    # FAMB HAS real DMPs (4/12) — it would license under the n-DMP chance null — but is BELOW background.
    assert famb.count_ttest == 4 and famb.count_rank == 4
    assert famb.fold_ttest < 1.0                            # 0.33 rate / 0.50 bg = 0.66x -> depleted
    assert famb.status != Status.LICENSED and famb.verdict != "LICENSED"

    # ONE shared ledger: exactly the enriched family is a discovery.
    assert res.corpus.fdr_ledger.n_discoveries == 1
    assert res.corpus.fdr_ledger.discoveries == frozenset({"te-fama-enrich"})
