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
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            if c[0] != chrom:
                continue
            pos = int(c[1])
            if pos < start:
                continue
            if pos >= end:
                continue
            yield pos, float(c[3]), int(c[4])


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
