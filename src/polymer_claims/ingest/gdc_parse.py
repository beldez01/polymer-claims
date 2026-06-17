"""Parsers for the three GDC open-access file types. Tolerant by column NAME (GDC harmonized
headers are stable, but locate columns by name, not position, where a header exists). Pure; no I/O."""
from __future__ import annotations


def _to_float(tok: str) -> float:
    tok = tok.strip()
    if tok in ("", "NA", "NaN", ".", "'--"):
        return float("nan")
    return float(tok)


def parse_beta_file(text: str) -> dict[str, float]:
    """GDC per-aliquot methylation beta file -> {probe_id: beta}. Cols 0,1. A first row whose
    2nd column isn't a float is treated as a header and skipped."""
    out: dict[str, float] = {}
    first = True  # header heuristic applies to the first NON-BLANK row (robust to leading blanks)
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        if first:
            first = False
            try:
                float(parts[1])
            except ValueError:
                continue  # header row
        out[parts[0].strip()] = _to_float(parts[1])
    return out


def parse_beta_meta(text: str) -> dict[str, dict]:
    """GDC per-aliquot methylation beta file -> {probe_id: {'chr': str, 'pos': int}}, read from the
    file's Chromosome/Start annotation columns located BY NAME from the header. EVERY probe in the
    file gets an entry (so downstream row_data/QC never KeyErrors); a probe whose annotation is
    absent/unparseable gets {'chr': '', 'pos': 0}. A file with no header/annotation columns yields
    the empty default for all probes. The annotation is platform-fixed, so callers parse it from ONE
    beta file."""
    out: dict[str, dict] = {}
    header: list[str] | None = None
    chr_i: int | None = None
    start_i: int | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        if header is None:
            try:
                float(parts[1])  # a float 2nd column => no header row; this line is data
            except ValueError:
                header = [p.strip() for p in parts]
                chr_i = header.index("Chromosome") if "Chromosome" in header else None
                start_i = header.index("Start") if "Start" in header else None
                continue
            header = []  # no header present; fall through and treat this first line as data
        chrom = parts[chr_i].strip() if chr_i is not None and chr_i < len(parts) else ""
        pos_tok = parts[start_i].strip() if start_i is not None and start_i < len(parts) else ""
        pos = int(pos_tok) if pos_tok.lstrip("-").isdigit() else 0
        out[parts[0].strip()] = {"chr": chrom, "pos": pos}
    return out


def parse_maf(text: str) -> list[dict]:
    """GDC MAF -> list of {Hugo_Symbol, HGVSp_Short, Tumor_Sample_Barcode}. Skips '#' comments."""
    rows: list[dict] = []
    header: list[str] | None = None
    want = ("Hugo_Symbol", "HGVSp_Short", "Tumor_Sample_Barcode")
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if header is None:
            header = parts
            continue
        rec = dict(zip(header, parts))
        rows.append({k: rec.get(k, "") for k in want})
    return rows


def parse_clinical(text: str) -> dict[str, dict]:
    """GDC clinical.tsv -> {case_id: {'Age': int|None, 'Sex': str}}. Reads case_submitter_id,
    age_at_index, gender by name."""
    out: dict[str, dict] = {}
    header: list[str] | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if header is None:
            header = parts
            continue
        rec = dict(zip(header, parts))
        case = rec.get("case_submitter_id", "").strip()
        if not case:
            continue
        age_tok = rec.get("age_at_index", "").strip()
        age = int(age_tok) if age_tok.isdigit() else None
        out[case] = {"Age": age, "Sex": rec.get("gender", "").strip()}
    return out
