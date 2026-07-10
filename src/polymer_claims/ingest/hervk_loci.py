"""HERV-K(HML-2) LTR element loci from the UCSC RepeatMasker track (rmsk.txt).

LTR5_Hs is the promoter-bearing 5' LTR of the youngest, most intact HERV-K(HML-2) proviruses. These
elements are scattered genome-wide (~630 on the standard chromosomes in hg38), so downstream code
gathers CpGs across ALL of them into one probe matrix (extract_cpg_matrix_multi).

rmsk.txt is the raw UCSC table dump: tab-separated, no header, standard column order (0-indexed):
    0 bin  1 swScore  2 milliDiv  3 milliDel  4 milliIns
    5 genoName  6 genoStart  7 genoEnd  8 genoLeft  9 strand
    10 repName  11 repClass  12 repFamily  ...
(verified against ~/Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt: an LTR5_Hs row reads
`... chr1 1409806 1410773 ... + LTR5_Hs LTR ERVK ...`). genoStart/genoEnd are 0-based half-open, which
matches the [start, end) windows extract_cpg_matrix_multi expects.
"""
from __future__ import annotations

import gzip
from pathlib import Path

_STD_CHROMS = frozenset([f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"])


def _open(path: Path):
    p = Path(path)
    return gzip.open(p, "rt") if p.suffix == ".gz" else open(p)


def hervk_ltr5_windows(rmsk_path: Path) -> list[tuple[str, int, int]]:
    """Parse rmsk.txt -> sorted list of (chrom, start, end) for HERV-K LTR5_Hs elements.

    Filters repName == "LTR5_Hs" AND repClass == "LTR" (the HML-2 promoter LTR) on standard chromosomes
    only (chr1..22, X, Y — drops _alt/_random/chrUn contigs). Windows are the element's [genoStart,
    genoEnd). Returned sorted by (chrom, start); deterministic.
    """
    out: list[tuple[str, int, int]] = []
    with _open(rmsk_path) as fh:
        for line in fh:
            c = line.rstrip("\n").split("\t")
            if len(c) < 12:
                continue
            geno_name, geno_start, geno_end = c[5], c[6], c[7]
            rep_name, rep_class = c[10], c[11]
            if rep_name != "LTR5_Hs" or rep_class != "LTR":
                continue
            if geno_name not in _STD_CHROMS:
                continue
            out.append((geno_name, int(geno_start), int(geno_end)))
    out.sort()
    return out
