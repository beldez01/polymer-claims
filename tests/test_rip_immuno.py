"""Task 5 — batch immuno methylation licensing driver over a synthetic mini-atlas.

No real data: a tiny in-tmp_path atlas (monocyte-open vs naive-T-methylated at one window)
exercises the full drive — single-pass extraction, per-locus content-addressed contract,
pre-registration in fixed panel order, and the two-independent-leg gate under one shrinking
e-LOND FDR budget.
"""
import gzip

from polymer_claims.rip_immuno import run


def _mini_atlas(tmp_path):
    bed = tmp_path / "bed"
    bed.mkdir()

    def w(stem, beta):
        with gzip.open(bed / f"{stem}.hg38.bed.gz", "wt") as fh:
            fh.write("#chr\tstart\tend\tbeta\ttotal_cov\ttotal_meth\tn_cpgs\n")
            for pos in (100, 150, 199):
                fh.write(f"chr6\t{pos}\t{pos+1}\t{beta:.4f}\t20\t{round(beta*20)}\t1\n")

    # Real signal at chr6:100-200: naive-T methylated (~0.8) vs monocyte open (~0.15).
    for s, b in [("Mono1", 0.15), ("Mono2", 0.16), ("T1", 0.80), ("T2", 0.82)]:
        w(s, b)
    man = tmp_path / "m.tsv"
    man.write_text(
        "gsm\tfilename_stem\tcell_type\tcell_type_broad\tlineage\treplicates\n"
        "G1\tMono1\tMonocytes\tMonocyte\tMyeloid\t1\n"
        "G2\tMono2\tMonocytes\tMonocyte\tMyeloid\t2\n"
        "G3\tT1\tT_Naive_CD4\tT_naive\tLymphoid\t1\n"
        "G4\tT2\tT_Naive_CD4\tT_naive\tLymphoid\t2\n"
    )
    return bed, man


def _panel(tmp_path, rows):
    p = tmp_path / "panel.tsv"
    hdr = "locus_id\tklass\tchrom\tstart\tend\tgroup_a\tgroup_b\tcomparator\ttau\trationale\n"
    p.write_text(hdr + "".join("\t".join(map(str, r)) + "\n" for r in rows))
    return p


def test_real_signal_licenses(tmp_path):
    bed, man = _mini_atlas(tmp_path)
    panel = _panel(tmp_path, [
        ("sig", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.10, "real"),
    ])
    res = run(panel, bed, man, tmp_path / "contracts")
    assert res.verdicts["sig"] == "LICENSED"


def test_fdr_budget_bites_at_volume(tmp_path):
    bed, man = _mini_atlas(tmp_path)
    # 1 real + several null loci over the SAME window; the nulls invert the comparator
    # direction (group_a/group_b swapped), so their Δβ is wrong-signed and they never license.
    rows = [("sig", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.10, "real")]
    rows += [
        (f"null{i}", "HLA", "chr6", 100, 200, "Monocyte", "T_naive", "GT", 0.10, "null")
        for i in range(6)
    ]
    res = run(_panel(tmp_path, rows), bed, man, tmp_path / "contracts")
    assert res.verdicts["sig"] == "LICENSED"
    assert all(res.verdicts[f"null{i}"] == "PENDING" for i in range(6))  # nulls never license
    # The e-LOND budget is genuinely charged in fixed panel order: 7 registered tests, α ∝ 1/t².
    assert res.corpus.fdr_ledger.n_tests == 7
    idxs = [t.index for t in res.corpus.fdr_ledger.tests]
    alphas = [t.alpha_allocated for t in res.corpus.fdr_ledger.tests]
    assert idxs == sorted(idxs)                          # registered in stream order
    assert all(a2 < a1 for a1, a2 in zip(alphas, alphas[1:]))  # budget shrinks down the panel


def test_post_hoc_tau_change_is_rejected(tmp_path):
    """A τ raised after the fact must NOT silently re-license: re-running with a τ the real
    Δβ cannot clear leaves the locus PENDING (no post-hoc rescue). The commitment is bound at
    registration, so the only way through the gate is a genuine effect that clears the
    pre-registered bar."""
    bed, man = _mini_atlas(tmp_path)
    panel = _panel(tmp_path, [
        ("sig", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.10, "real"),
    ])
    res = run(panel, bed, man, tmp_path / "c1")
    assert res.verdicts["sig"] == "LICENSED"
    # τ = 0.90 exceeds the real Δβ (≈0.65): the locus cannot clear the moved bar and stays PENDING.
    panel2 = _panel(tmp_path, [
        ("sig", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.90, "real"),
    ])
    res2 = run(panel2, bed, man, tmp_path / "c2")
    assert res2.verdicts["sig"] == "PENDING"
