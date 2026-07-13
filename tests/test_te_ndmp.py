"""TE-family n-DMP SWEEP driver (te_ndmp.run_te_family_sweep).

Synthetic, no real data. Two families through ONE shared e-LOND ledger:
  * a strongly lineage-separated family LICENSES (discovery at its pre-registered slot),
  * a flat (non-separating) family stays PENDING,
proving the shared-ledger sweep resolves each family at its own locked alpha (match-gate) and that a
mixed licensed/pending outcome comes out right. The REAL drive is scripts/rip_te_families_ndmp.py.
"""
from __future__ import annotations

import gzip
import math

from polymer_grammar import FDRLedger, Status, register_test

from polymer_claims.rip_mhc_ndmp import preregistered_k
from polymer_claims.te_ndmp import PANEL, TeFamilySpec, run_te_family_sweep


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


# Two families, disjoint genomic windows. FAMA (chr2) separates Lymphoid~0.9 / Myeloid~0.1 on every
# probe; FAMB (chr3) is flat ~0.5 in both lineages (jittered so variance is nonzero, p-values ~1).
_FAMA_WIN = ("chr2", 1000, 1200)
_FAMB_WIN = ("chr3", 2000, 2200)
_WINMAP = {"FAMA": [_FAMA_WIN], "FAMB": [_FAMB_WIN]}


def _atlas(tmp_path, *, n_per_group=5, n_probes=6):
    bed = tmp_path / "bed"
    bed.mkdir()
    pos_a = [1000 + 10 * i for i in range(n_probes)]
    pos_b = [2000 + 10 * i for i in range(n_probes)]

    def w(stem, sep_base, flat_base):
        rows = []
        for j, p in enumerate(pos_a):  # separating family
            rows.append(("chr2", p, min(0.99, max(0.01, sep_base + 0.003 * j)), 20))
        for j, p in enumerate(pos_b):  # flat family — same distribution in both lineages
            rows.append(("chr3", p, min(0.99, max(0.01, flat_base + 0.004 * j)), 20))
        _write_bed(bed / f"{stem}.hg38.bed.gz", rows)

    entries = []
    for i in range(n_per_group):
        w(f"Ly{i}", 0.88 + 0.01 * i, 0.50 + 0.01 * i)
        w(f"My{i}", 0.10 + 0.01 * i, 0.50 + 0.01 * i)   # flat_base identical to Ly -> no group effect
        entries += [(f"Ly{i}", "Lymphoid"), (f"My{i}", "Myeloid")]
    man = tmp_path / "m.tsv"
    _manifest(man, entries)
    return bed, man


_TEST_PANEL = (
    TeFamilySpec("fama", "FAMA", "LTR", "FAMA separating family", "synthetic: strong lineage split"),
    TeFamilySpec("famb", "FAMB", "LTR", "FAMB flat family", "synthetic: no lineage split"),
)


def test_sweep_licenses_separating_family_and_holds_flat_family(tmp_path, monkeypatch):
    # 12 complete-case probes: enough that a perfectly-separated family's count e-value clears the
    # severe slot-1 bar (~32.9). At 6 probes it lands just under (32.0) — the gate is genuinely severe.
    bed, man = _atlas(tmp_path, n_per_group=5, n_probes=12)
    import polymer_claims.te_ndmp as drv
    # rmsk parse is stubbed to synthetic windows (keyed by family key); the atlas pass runs for real
    # over the synthetic BEDs via extract_cpg_matrices_multi_families.
    monkeypatch.setattr(drv, "te_family_windows_multi",
                        lambda _p, specs: {key: _WINMAP[rn] for key, rn, _rc in specs})

    res = run_te_family_sweep(
        "unused_rmsk", bed, man, tmp_path / "contracts",
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4, panel=_TEST_PANEL,
    )

    by_key = {f.key: f for f in res.families}
    assert set(by_key) == {"fama", "famb"}

    fama = by_key["fama"]
    assert fama.n_windows == 1 and fama.n_probes == 12
    assert fama.k == preregistered_k(12, 0.05)     # ceil(3*0.05*12) = 2
    assert fama.count_ttest == 12 and fama.count_rank == 12   # every probe separates
    assert fama.status == Status.LICENSED and fama.verdict == "LICENSED"
    assert fama.e_value is not None and fama.bar is not None and fama.e_value >= fama.bar

    famb = by_key["famb"]
    assert famb.n_probes == 12
    assert famb.count_ttest == 0 and famb.count_rank == 0   # flat -> no DMPs
    assert famb.status != Status.LICENSED and famb.verdict != "LICENSED"

    # ONE shared ledger: exactly the separating family is a discovery.
    assert res.corpus.fdr_ledger.n_discoveries == 1
    assert res.corpus.fdr_ledger.discoveries == frozenset({"te-fama-ndmp"})


def test_preregistration_locks_a_stricter_bar_per_later_slot(tmp_path):
    """With no discoveries yet at registration time, slot t locks alpha_t = target*gamma_t
    (gamma_t = (6/pi^2)/t^2), so the bar 1/alpha_t = pi^2 * t^2 / (6*target) grows with t. Registration
    ORDER therefore fixes the bar each family faces — the crux of pre-registration integrity."""
    ledger = FDRLedger(target_fdr=0.05)
    for i in range(1, 5):
        ledger = register_test(ledger, f"claim-{i}", f"h{i}")
    bars = [1.0 / t.alpha_allocated for t in ledger.tests]
    assert bars == sorted(bars)                      # strictly non-decreasing (later = stricter)
    for t, entry in enumerate(ledger.tests, start=1):
        expected = math.pi**2 * t * t / (6.0 * 0.05)
        assert abs(1.0 / entry.alpha_allocated - expected) < 1e-9


def test_real_panel_is_wellformed():
    """The committed PANEL is the pre-registration artifact: distinct keys/claim-stems, fixed order."""
    keys = [s.key for s in PANEL]
    assert len(keys) == len(set(keys))               # no duplicate slots
    assert keys[0] == "hervk_ltr5"                   # positive control registered first (documented)
    assert all(s.rep_name and s.rep_class for s in PANEL)
