"""Loyfer 2023 WGBS atlas: per-CpG bed/tabix extractor -> per-sample mean beta over a locus window.

Reads GEO-derived per-CpG bed.gz files (chr, start, end, beta, total_cov, total_meth, n_cpgs)
plus a sample manifest, and returns QC-filtered per-sample mean methylation over a region.
"""
from __future__ import annotations
import gzip
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SampleBeta:
    sample: str; cell_type: str; cell_type_broad: str; lineage: str
    beta: float; n_cpg: int; mean_cov: float


def load_manifest(path: Path) -> list[tuple[str, str, str, str]]:
    rows = [ln.split("\t") for ln in Path(path).read_text().splitlines() if ln.strip()]
    hdr = rows[0]
    i_stem, i_ct, i_br, i_ln = (hdr.index(c) for c in
                                ("filename_stem", "cell_type", "cell_type_broad", "lineage"))
    return [(r[i_stem], r[i_ct], r[i_br], r[i_ln]) for r in rows[1:]]


def _parse_bed_line(line: str) -> tuple[str, int, float, int] | None:
    """Parse one atlas bed.gz data line -> (chrom, pos, beta, cov), or None for comments/blanks."""
    if not line or line.startswith("#"):
        return None
    c = line.rstrip("\n").split("\t")
    return c[0], int(c[1]), float(c[3]), int(c[4])


def _iter_region(bed_path: Path, chrom: str, start: int, end: int):
    """Yield (pos, beta, cov) for CpGs in [start, end). Tabix if available, else stream-scan."""
    try:
        import pysam
        if (bed_path.parent / (bed_path.name + ".tbi")).exists() or Path(str(bed_path) + ".tbi").exists():
            with pysam.TabixFile(str(bed_path)) as tb:
                for line in tb.fetch(chrom, start, end):
                    c = line.split("\t")
                    yield int(c[1]), float(c[3]), int(c[4])
                return
    except Exception:
        pass
    with gzip.open(bed_path, "rt") as fh:
        for line in fh:
            parsed = _parse_bed_line(line)
            if parsed is None:
                continue
            c_chrom, pos, beta, cov = parsed
            if c_chrom != chrom:
                continue
            if pos < start:
                continue
            if pos >= end:
                continue
            yield pos, beta, cov


def _find_bed(bed_dir: Path, stem: str) -> Path | None:
    hits = sorted(bed_dir.glob(f"*{stem}*.bed.gz"))
    return hits[0] if hits else None


def extract_region(bed_dir: Path, manifest: Path, chrom: str, start: int, end: int,
                   *, min_cov: int = 4, min_cpg: int = 3) -> list[SampleBeta]:
    out: list[SampleBeta] = []
    for stem, ct, br, ln in load_manifest(manifest):
        bed = _find_bed(Path(bed_dir), stem)
        if bed is None:
            continue
        betas, covs = [], []
        try:
            for _pos, beta, cov in _iter_region(bed, chrom, start, end):
                if cov >= min_cov:
                    betas.append(beta); covs.append(cov)
        except (OSError, EOFError):
            continue  # truncated/corrupt source bed.gz for this sample: skip, don't crash the batch
        if len(betas) < min_cpg:
            continue  # QC-drop: PENDING(unpowered) decided downstream by group size
        out.append(SampleBeta(sample=stem, cell_type=ct, cell_type_broad=br, lineage=ln,
                              beta=sum(betas) / len(betas), n_cpg=len(betas),
                              mean_cov=sum(covs) / len(covs)))
    return out


def extract_regions_multi(
    bed_dir: Path, manifest: Path,
    windows: list[tuple[str, str, int, int]],  # (locus_id, chrom, start, end)
    *, min_cov: int = 4, min_cpg: int = 3,
) -> dict[str, list[SampleBeta]]:
    """Scan each sample bed.gz ONCE, accumulating per-CpG betas for every window it overlaps.

    Returns locus_id -> [SampleBeta], same per-sample QC as extract_region (mean of per-CpG beta
    over CpGs with cov >= min_cov; a sample with surviving n_cpg < min_cpg is dropped for that
    locus). Must agree exactly with calling extract_region once per window.
    """
    by_chrom: dict[str, list[tuple[str, int, int]]] = {}
    for locus_id, chrom, start, end in windows:
        by_chrom.setdefault(chrom, []).append((locus_id, start, end))

    result: dict[str, list[SampleBeta]] = {locus_id: [] for locus_id, _, _, _ in windows}

    for stem, ct, br, ln in load_manifest(manifest):
        bed = _find_bed(Path(bed_dir), stem)
        if bed is None:
            continue
        acc: dict[str, tuple[list[float], list[int]]] = {locus_id: ([], []) for locus_id, _, _, _ in windows}
        try:
            with gzip.open(bed, "rt") as fh:
                for line in fh:
                    parsed = _parse_bed_line(line)
                    if parsed is None:
                        continue
                    chrom, pos, beta, cov = parsed
                    wins = by_chrom.get(chrom)
                    if not wins or cov < min_cov:
                        continue
                    for locus_id, start, end in wins:
                        if start <= pos < end:
                            betas, covs = acc[locus_id]
                            betas.append(beta)
                            covs.append(cov)
        except (OSError, EOFError):
            continue  # truncated/corrupt source bed.gz for this sample: skip, don't crash the batch
        for locus_id, (betas, covs) in acc.items():
            if len(betas) < min_cpg:
                continue  # QC-drop: PENDING(unpowered) decided downstream by group size
            result[locus_id].append(SampleBeta(
                sample=stem, cell_type=ct, cell_type_broad=br, lineage=ln,
                beta=sum(betas) / len(betas), n_cpg=len(betas),
                mean_cov=sum(covs) / len(covs)))
    return result
