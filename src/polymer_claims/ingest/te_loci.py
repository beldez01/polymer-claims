"""Transposable-element loci from the UCSC RepeatMasker track (rmsk.txt).

Generalizes ``hervk_loci.hervk_ltr5_windows`` (which hard-codes ``repName == "LTR5_Hs"`` and
``repClass == "LTR"``) to any TE subfamily, so one selector can drive a whole family sweep. Same rmsk
column contract, same [start, end) half-open windows, same standard-chromosome filter, same
deterministic sort — only the match predicate is parameterized.

rmsk.txt is the raw UCSC table dump: tab-separated, no header, standard column order (0-indexed):
    0 bin  1 swScore  2 milliDiv  3 milliDel  4 milliIns
    5 genoName  6 genoStart  7 genoEnd  8 genoLeft  9 strand
    10 repName  11 repClass  12 repFamily  ...
genoStart/genoEnd are 0-based half-open, matching the [start, end) windows
``extract_cpg_matrix_multi`` expects.
"""
from __future__ import annotations

import gzip
import random
from pathlib import Path

_STD_CHROMS = frozenset([f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"])

# GRCh38/hg38 primary-assembly chromosome lengths (bp). Used only to place random background windows
# in-bounds; a few bp of imprecision is immaterial to uniform genome sampling.
_HG38_STD_SIZES: dict[str, int] = {
    "chr1": 248956422, "chr2": 242193529, "chr3": 198295559, "chr4": 190214555,
    "chr5": 181538259, "chr6": 170805979, "chr7": 159345973, "chr8": 145138636,
    "chr9": 138394717, "chr10": 133797422, "chr11": 135086622, "chr12": 133275309,
    "chr13": 114364328, "chr14": 107043718, "chr15": 101991189, "chr16": 90338345,
    "chr17": 83257441, "chr18": 80373285, "chr19": 58617616, "chr20": 64444167,
    "chr21": 46709983, "chr22": 50818468, "chrX": 156040895, "chrY": 57227415,
}


def random_background_windows(
    n: int, size: int, seed: int, *, chrom_sizes: dict[str, int] = _HG38_STD_SIZES
) -> list[tuple[str, int, int]]:
    """`n` random [start, start+size) windows placed uniformly across the genome (chromosome chosen with
    probability proportional to its length), deterministic given `seed`. The matched-background control
    for the TE-family sweep: run these through the SAME n-DMP gate and compare the lineage-DMP fraction
    to the TE families' — the test of whether TEs are *enriched* vs a genomic baseline, not merely
    differentially methylated beyond chance. Returned sorted by (chrom, start, end)."""
    rng = random.Random(seed)
    chroms = list(chrom_sizes)
    weights = [chrom_sizes[c] for c in chroms]
    out: list[tuple[str, int, int]] = []
    for _ in range(n):
        c = rng.choices(chroms, weights=weights, k=1)[0]
        start = rng.randint(0, chrom_sizes[c] - size)
        out.append((c, start, start + size))
    out.sort()
    return out


def _open(path: Path):
    p = Path(path)
    return gzip.open(p, "rt") if p.suffix == ".gz" else open(p)


def te_family_windows(
    rmsk_path: Path,
    *,
    rep_name: str | None = None,
    rep_class: str | None = None,
    rep_family: str | None = None,
) -> list[tuple[str, int, int]]:
    """Parse rmsk.txt -> sorted list of (chrom, start, end) for one TE subfamily.

    A row matches when EVERY supplied field equals the row's value; fields left ``None`` are
    unconstrained. At least one of ``rep_name`` / ``rep_class`` / ``rep_family`` must be given (an
    all-``None`` call would select every repeat genome-wide, never what a family claim intends).
    Standard chromosomes only (chr1..22, X, Y — drops _alt/_random/chrUn). Windows are the element's
    [genoStart, genoEnd). Returned sorted by (chrom, start, end); deterministic.
    """
    if rep_name is None and rep_class is None and rep_family is None:
        raise ValueError("te_family_windows: give at least one of rep_name/rep_class/rep_family")
    out: list[tuple[str, int, int]] = []
    with _open(rmsk_path) as fh:
        for line in fh:
            c = line.rstrip("\n").split("\t")
            if len(c) < 13:
                continue
            geno_name, geno_start, geno_end = c[5], c[6], c[7]
            r_name, r_class, r_family = c[10], c[11], c[12]
            if rep_name is not None and r_name != rep_name:
                continue
            if rep_class is not None and r_class != rep_class:
                continue
            if rep_family is not None and r_family != rep_family:
                continue
            if geno_name not in _STD_CHROMS:
                continue
            out.append((geno_name, int(geno_start), int(geno_end)))
    out.sort()
    return out


def te_family_windows_multi(
    rmsk_path: Path, specs: list[tuple[str, str, str]]
) -> dict[str, list[tuple[str, int, int]]]:
    """Parse rmsk.txt ONCE and bucket windows for MANY families.

    `specs` is a list of (key, rep_name, rep_class); returns {key: sorted [(chrom,start,end)]}. The
    result for each key equals `te_family_windows(rmsk, rep_name=…, rep_class=…)` — one full-file scan
    total instead of one per family. A (rep_name, rep_class) pair may map to multiple keys (each gets
    its own list)."""
    buckets: dict[str, list[tuple[str, int, int]]] = {key: [] for key, _, _ in specs}
    by_match: dict[tuple[str, str], list[str]] = {}
    for key, rn, rc in specs:
        by_match.setdefault((rn, rc), []).append(key)
    with _open(rmsk_path) as fh:
        for line in fh:
            c = line.rstrip("\n").split("\t")
            if len(c) < 13:
                continue
            geno_name, geno_start, geno_end = c[5], c[6], c[7]
            keys = by_match.get((c[10], c[11]))
            if not keys or geno_name not in _STD_CHROMS:
                continue
            win = (geno_name, int(geno_start), int(geno_end))
            for key in keys:
                buckets[key].append(win)
    for key in buckets:
        buckets[key].sort()
    return buckets
