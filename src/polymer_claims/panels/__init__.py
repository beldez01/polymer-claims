"""Pre-registerable locus panels for the immuno/ERV methylation licensing drive.

`LocusSpec` rows are authored from annotation only (gene TSS + RepeatMasker
repName/coordinates) — never from the Loyfer atlas itself, so panel authorship
stays pre-registration-safe. `coverage_precheck` is the one function allowed to
touch the atlas pre-registration, and it reads coverage only (never the effect),
to prune loci that can't be powered before any claim is scored.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocusSpec:
    locus_id: str
    klass: str
    chrom: str
    start: int
    end: int
    group_a: str
    group_b: str
    comparator: str
    tau: float
    rationale: str


_PANEL_COLUMNS = (
    "locus_id", "klass", "chrom", "start", "end",
    "group_a", "group_b", "comparator", "tau", "rationale",
)

_HG38_CHR1_END = 248_956_422  # sentinel: hg38 chr1 assembly length (GRCh38.p14)


def load_panel(path: Path) -> list[LocusSpec]:
    """Parse the panel TSV, preserving row order (order is a pre-registered degree of freedom)."""
    rows = [ln.split("\t") for ln in Path(path).read_text().splitlines() if ln.strip()]
    if not rows:
        return []
    hdr = rows[0]
    idx = {c: i for i, c in enumerate(hdr)}
    missing = [c for c in _PANEL_COLUMNS if c not in idx]
    if missing:
        raise ValueError(f"panel {path} missing required columns: {missing}")
    out = []
    for r in rows[1:]:
        out.append(LocusSpec(
            locus_id=r[idx["locus_id"]],
            klass=r[idx["klass"]],
            chrom=r[idx["chrom"]],
            start=int(r[idx["start"]]),
            end=int(r[idx["end"]]),
            group_a=r[idx["group_a"]],
            group_b=r[idx["group_b"]],
            comparator=r[idx["comparator"]],
            tau=float(r[idx["tau"]]),
            rationale=r[idx["rationale"]],
        ))
    return out


def assert_rmsk_hg38(rmsk_path: Path) -> None:
    """Hard-fail unless rmsk.txt is hg38: every chr1 record must end <= hg38 chr1 length.

    Locates the chrom field dynamically (searches each row for a literal "chr1" token,
    genoStart/genoEnd assumed to be the two fields immediately after it) rather than
    assuming a fixed column index — real UCSC rmsk.txt has 5 leading numeric fields
    (bin, swScore, milliDiv, milliDel, milliIns) before genoName, which a hardcoded
    index would get wrong.
    """
    max_chr1_end = 0
    for ln in Path(rmsk_path).read_text().splitlines():
        c = ln.split("\t")
        try:
            i = c.index("chr1")
        except ValueError:
            continue
        if len(c) > i + 2:
            try:
                end = int(c[i + 2])
            except ValueError:
                continue
            max_chr1_end = max(max_chr1_end, end)
    if max_chr1_end == 0 or max_chr1_end > _HG38_CHR1_END:
        raise ValueError(
            f"rmsk.txt does not look like hg38 (chr1 max end {max_chr1_end} "
            f"> hg38 {_HG38_CHR1_END}); refusing to trust TE coordinates"
        )


def coverage_precheck(panel, bed_dir, manifest, *, min_cov: int = 4, min_cpg: int = 3) -> dict[str, bool]:
    """locus_id -> powerable? (both groups keep >=2 samples after QC).

    Reads coverage only, never the effect — safe to run pre-registration to prune
    unpowerable loci without touching the comparison this panel will be scored on.
    """
    from ..ingest.loyfer_wgbs import extract_regions_multi
    windows = [(loc.locus_id, loc.chrom, loc.start, loc.end) for loc in panel]
    by_locus = extract_regions_multi(Path(bed_dir), Path(manifest), windows,
                                      min_cov=min_cov, min_cpg=min_cpg)
    ok: dict[str, bool] = {}
    for loc in panel:
        rows = by_locus[loc.locus_id]
        a = sum(1 for r in rows if r.cell_type_broad == loc.group_a)
        b = sum(1 for r in rows if r.cell_type_broad == loc.group_b)
        ok[loc.locus_id] = a >= 2 and b >= 2
    return ok
