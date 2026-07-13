"""Loyfer 2023 WGBS atlas: per-CpG bed/tabix extractor -> per-sample mean beta over a locus window.

Reads GEO-derived per-CpG bed.gz files (chr, start, end, beta, total_cov, total_meth, n_cpgs)
plus a sample manifest, and returns QC-filtered per-sample mean methylation over a region.
"""
from __future__ import annotations
import bisect
import gzip
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SampleBeta:
    sample: str; cell_type: str; cell_type_broad: str; lineage: str
    beta: float; n_cpg: int; mean_cov: float


@dataclass(frozen=True)
class CpgMatrix:
    probe_ids: list[str]                 # "chr6:29942123" per retained CpG, in genomic order
    samples: list[str]                   # filename_stem per retained sample, stable order
    sample_meta: list[dict]              # per sample: {"sample","cell_type","cell_type_broad","lineage"}
    betas: list[list[float]]             # betas[p][s] = beta of probe p in sample s


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


def extract_cpg_matrix(
    bed_dir: Path, manifest: Path, chrom: str, start: int, end: int,
    *, min_cov: int = 4, require_all_samples: bool = True,
) -> CpgMatrix:
    """Single pass per sample bed.gz over [start,end): collect per-CpG beta where cov>=min_cov.

    Then align across samples on genomic position. require_all_samples=True (default, the tested
    path) keeps the COMPLETE-CASE probe set: CpG positions covered (>=min_cov) in EVERY retained
    sample, aligned in genomic order. require_all_samples=False instead keeps the union of covered
    positions across samples, filling gaps with float('nan'). A sample with zero covered CpGs in
    the window is dropped before the intersection/union is computed. Deterministic; no clock/random.
    """
    per_sample: list[dict[int, float]] = []
    kept_meta: list[tuple[str, str, str, str]] = []
    for stem, ct, br, ln in load_manifest(manifest):
        bed = _find_bed(Path(bed_dir), stem)
        if bed is None:
            continue
        pos_beta: dict[int, float] = {}
        try:
            for pos, beta, cov in _iter_region(bed, chrom, start, end):
                if cov >= min_cov:
                    pos_beta[pos] = beta
        except (OSError, EOFError):
            continue  # truncated/corrupt source bed.gz for this sample: skip, don't crash the batch
        if not pos_beta:
            continue  # sample with zero covered CpGs in the window: dropped
        per_sample.append(pos_beta)
        kept_meta.append((stem, ct, br, ln))

    if not per_sample:
        return CpgMatrix(probe_ids=[], samples=[], sample_meta=[], betas=[])

    if require_all_samples:
        common = set(per_sample[0])
        for pb in per_sample[1:]:
            common &= set(pb)
        positions = sorted(common)
        betas = [[pb[pos] for pb in per_sample] for pos in positions]
    else:
        all_pos: set[int] = set()
        for pb in per_sample:
            all_pos |= set(pb)
        positions = sorted(all_pos)
        betas = [[pb.get(pos, float("nan")) for pb in per_sample] for pos in positions]

    probe_ids = [f"{chrom}:{pos}" for pos in positions]
    samples = [stem for stem, _, _, _ in kept_meta]
    sample_meta = [{"sample": stem, "cell_type": ct, "cell_type_broad": br, "lineage": ln}
                   for stem, ct, br, ln in kept_meta]
    return CpgMatrix(probe_ids=probe_ids, samples=samples, sample_meta=sample_meta, betas=betas)


def extract_cpg_matrix_multi(
    bed_dir: Path, manifest: Path, windows: list[tuple[str, int, int]],
    *, min_cov: int = 4,
) -> CpgMatrix:
    """Complete-case CpG matrix over the UNION of CpGs falling in ANY of `windows`.

    `windows` is a list of (chrom, start, end) half-open intervals (HERV-K LTR elements are scattered
    genome-wide, so one probe matrix is gathered across MANY small windows). Each sample bed.gz is
    scanned ONCE (there is no per-sample tabix index for this atlas, so a per-window fetch would rescan
    the whole file W times); every CpG with cov>=min_cov landing in some window is collected, keyed by
    (chrom, pos). Then the COMPLETE-CASE probe set is kept: positions covered in EVERY retained sample.
    A sample with zero covered CpGs across all windows is dropped before the intersection.

    On a single window this is identical to extract_cpg_matrix(require_all_samples=True): same covered
    positions, same complete-case intersection, same "chrom:pos" probe ids (a test asserts agreement).
    Deterministic; no clock/random. Probe order is sorted (chrom, pos).
    """
    # Index windows by chrom, merged into disjoint (non-overlapping) intervals so the bisect
    # membership test below is correct even when input windows overlap or nest: a plain
    # "rightmost start <= pos" lookup against the RAW windows can pick a narrower nested window
    # and miss a CpG that is inside a larger, earlier-starting window (see test_loyfer_cpg_matrix.py).
    by_chrom: dict[str, list[tuple[int, int]]] = {}
    for chrom, start, end in windows:
        by_chrom.setdefault(chrom, []).append((start, end))
    merged_by_chrom: dict[str, list[tuple[int, int]]] = {}
    for chrom, wl in by_chrom.items():
        wl.sort()
        merged: list[list[int]] = []
        for start, end in wl:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        merged_by_chrom[chrom] = [(s, e) for s, e in merged]
    starts: dict[str, list[int]] = {chrom: [s for s, _ in wl] for chrom, wl in merged_by_chrom.items()}

    def _in_any_window(chrom: str, pos: int) -> bool:
        wl = merged_by_chrom.get(chrom)
        if not wl:
            return False
        i = bisect.bisect_right(starts[chrom], pos) - 1  # rightmost merged interval whose start <= pos
        return i >= 0 and pos < wl[i][1]

    per_sample: list[dict[tuple[str, int], float]] = []
    kept_meta: list[tuple[str, str, str, str]] = []
    for stem, ct, br, ln in load_manifest(manifest):
        bed = _find_bed(Path(bed_dir), stem)
        if bed is None:
            continue
        pos_beta: dict[tuple[str, int], float] = {}
        try:
            with gzip.open(bed, "rt") as fh:
                for line in fh:
                    parsed = _parse_bed_line(line)
                    if parsed is None:
                        continue
                    chrom, pos, beta, cov = parsed
                    if cov < min_cov:
                        continue
                    if _in_any_window(chrom, pos):
                        pos_beta[(chrom, pos)] = beta
        except (OSError, EOFError):
            continue  # truncated/corrupt source bed.gz for this sample: skip, don't crash the batch
        if not pos_beta:
            continue  # sample with zero covered CpGs across all windows: dropped
        per_sample.append(pos_beta)
        kept_meta.append((stem, ct, br, ln))

    if not per_sample:
        return CpgMatrix(probe_ids=[], samples=[], sample_meta=[], betas=[])

    common = set(per_sample[0])
    for pb in per_sample[1:]:
        common &= set(pb)
    keys = sorted(common)  # (chrom, pos) tuples: deterministic order
    betas = [[pb[key] for pb in per_sample] for key in keys]

    probe_ids = [f"{chrom}:{pos}" for chrom, pos in keys]
    samples = [stem for stem, _, _, _ in kept_meta]
    sample_meta = [{"sample": stem, "cell_type": ct, "cell_type_broad": br, "lineage": ln}
                   for stem, ct, br, ln in kept_meta]
    return CpgMatrix(probe_ids=probe_ids, samples=samples, sample_meta=sample_meta, betas=betas)


def _merged_membership(windows: list[tuple[str, int, int]]):
    """Merge (chrom,start,end) windows into disjoint intervals and return a `(chrom,pos)->bool`
    membership test. Same merge+bisect logic as extract_cpg_matrix_multi (nested/overlapping windows
    are merged so a plain rightmost-start bisect can't shadow a larger enclosing window)."""
    by_chrom: dict[str, list[tuple[int, int]]] = {}
    for chrom, start, end in windows:
        by_chrom.setdefault(chrom, []).append((start, end))
    merged_by_chrom: dict[str, list[tuple[int, int]]] = {}
    for chrom, wl in by_chrom.items():
        wl.sort()
        merged: list[list[int]] = []
        for start, end in wl:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        merged_by_chrom[chrom] = [(s, e) for s, e in merged]
    starts = {chrom: [s for s, _ in wl] for chrom, wl in merged_by_chrom.items()}

    def _in(chrom: str, pos: int) -> bool:
        wl = merged_by_chrom.get(chrom)
        if not wl:
            return False
        i = bisect.bisect_right(starts[chrom], pos) - 1
        return i >= 0 and pos < wl[i][1]

    return _in


def _complete_case_matrix(per_sample, kept_meta) -> CpgMatrix:
    """The shared tail of the multi-window extractors: complete-case intersection over the samples
    that had >=1 covered CpG, in sorted (chrom,pos) order. Identical to extract_cpg_matrix_multi's."""
    if not per_sample:
        return CpgMatrix(probe_ids=[], samples=[], sample_meta=[], betas=[])
    common = set(per_sample[0])
    for pb in per_sample[1:]:
        common &= set(pb)
    keys = sorted(common)
    betas = [[pb[key] for pb in per_sample] for key in keys]
    return CpgMatrix(
        probe_ids=[f"{chrom}:{pos}" for chrom, pos in keys],
        samples=[stem for stem, _, _, _ in kept_meta],
        sample_meta=[{"sample": s, "cell_type": ct, "cell_type_broad": br, "lineage": ln}
                     for s, ct, br, ln in kept_meta],
        betas=betas,
    )


def extract_cpg_matrices_multi_families(
    bed_dir: Path, manifest: Path, family_windows: dict[str, list[tuple[str, int, int]]],
    *, min_cov: int = 4,
) -> dict[str, CpgMatrix]:
    """Complete-case CpG matrices for MANY families in ONE pass over the atlas.

    `family_windows` maps family-key -> its list of (chrom,start,end) windows. Each sample bed.gz is
    scanned ONCE; every CpG with cov>=min_cov is routed to EACH family whose windows contain it. Then,
    PER FAMILY, the complete-case probe set is taken (positions covered in every sample that had >=1
    covered CpG in THAT family). The result for family F is byte-identical to
    `extract_cpg_matrix_multi(bed_dir, manifest, family_windows[F], min_cov=min_cov)` — the only change
    is that the ~47 sample BEDs are decompressed once total instead of once per family (a ~N_families
    speedup, since gzip decompression dominates). A global-union pre-filter keeps the common case (a CpG
    in no family's windows) at one bisect.
    """
    fams = list(family_windows)
    fam_member = {f: _merged_membership(family_windows[f]) for f in fams}
    all_windows = [w for f in fams for w in family_windows[f]]
    in_union = _merged_membership(all_windows)  # cheap pre-filter: skip CpGs in no window at all

    per_family_samples: dict[str, list[dict[tuple[str, int], float]]] = {f: [] for f in fams}
    per_family_meta: dict[str, list[tuple[str, str, str, str]]] = {f: [] for f in fams}

    for stem, ct, br, ln in load_manifest(manifest):
        bed = _find_bed(Path(bed_dir), stem)
        if bed is None:
            continue
        fam_pos_beta: dict[str, dict[tuple[str, int], float]] = {f: {} for f in fams}
        try:
            with gzip.open(bed, "rt") as fh:
                for line in fh:
                    parsed = _parse_bed_line(line)
                    if parsed is None:
                        continue
                    chrom, pos, beta, cov = parsed
                    if cov < min_cov or not in_union(chrom, pos):
                        continue
                    for f in fams:
                        if fam_member[f](chrom, pos):
                            fam_pos_beta[f][(chrom, pos)] = beta
        except (OSError, EOFError):
            continue  # truncated/corrupt source bed.gz: skip, don't crash the batch
        for f in fams:
            if fam_pos_beta[f]:  # per-family sample drop: identical to the single-family path
                per_family_samples[f].append(fam_pos_beta[f])
                per_family_meta[f].append((stem, ct, br, ln))

    return {f: _complete_case_matrix(per_family_samples[f], per_family_meta[f]) for f in fams}
