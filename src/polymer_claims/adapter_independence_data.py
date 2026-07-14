"""Loader for the adapter-independence live run (C1 Step 0) — AlphaMissense vs ESM1v on ClinVar.

Parses three tables, aligns them on the normalized variant key ``(chrom, pos, ref, alt)`` (GRCh38 /
hg38), and feeds C1's ``independence_report`` to measure whether the two predictors' ERRORS correlate
(the D4 air-gap question). NEVER fabricates scores — the live path runs only on real files the
operator supplies. The parsing logic is unit-tested on a tiny committed fixture.

Expected files under a data dir (gitignored; the operator drops the real data):
  * ``clinvar_variant_summary.tsv[.gz]`` — NCBI ClinVar variant_summary. Uses columns ``Assembly``
    (kept == "GRCh38"), ``Type`` (kept == "single nucleotide variant"), ``ClinicalSignificance``
    (→ binary label: Pathogenic/Likely pathogenic = 1, Benign/Likely benign = 0, else dropped), and
    the VCF key columns ``Chromosome`` / ``PositionVCF`` / ``ReferenceAlleleVCF`` / ``AlternateAlleleVCF``.
  * ``AlphaMissense_hg38.tsv[.gz]`` — columns ``CHROM POS REF ALT … am_pathogenicity`` (higher = more
    pathogenic). ``##``-prefixed metadata lines are skipped; a leading ``#`` on the header is stripped.
  * ``esm1v_llr.tsv[.gz]`` — columns ``chrom pos ref alt esm1v`` (masked-marginal LLR; LOWER = more
    deleterious, so it is negated to align direction with pathogenicity).

Leakage caveat (operator's): both models were developed against ClinVar-adjacent data — prefer
variants added/updated AFTER each model's cutoff, and report the leakage caveat with the result.
"""
from __future__ import annotations

import csv
import gzip
from pathlib import Path

from polymer_claims.adapter_independence import IndependenceReport, independence_report

_PATHOGENIC = {"Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic"}
_BENIGN = {"Benign", "Likely benign", "Benign/Likely benign"}

_VariantKey = tuple[str, str, str, str]


def _open(path: str | Path):
    p = Path(path)
    return gzip.open(p, "rt") if p.suffix == ".gz" else open(p)


def _key(chrom, pos, ref, alt) -> _VariantKey:
    return (str(chrom).removeprefix("chr"), str(pos), str(ref).upper(), str(alt).upper())


def _rows(path: str | Path):
    """Yield dict rows from a (optionally gzipped) TSV. Skips ``##`` metadata; the first remaining
    line is the header (a single leading ``#`` is stripped, per ClinVar's convention)."""
    with _open(path) as fh:
        header = None
        for line in fh:
            if line.startswith("##"):
                continue
            header = line.lstrip("#").rstrip("\n").split("\t")
            break
        if header is None:
            return
        yield from csv.DictReader(fh, fieldnames=header, delimiter="\t")


def load_clinvar_labels(path: str | Path) -> dict[_VariantKey, float]:
    """GRCh38 SNVs with an unambiguous clinical significance → {variant key: 1.0 pathogenic / 0.0 benign}."""
    out: dict[_VariantKey, float] = {}
    for r in _rows(path):
        if r.get("Assembly") != "GRCh38" or r.get("Type") != "single nucleotide variant":
            continue
        sig = r.get("ClinicalSignificance", "")
        label = 1.0 if sig in _PATHOGENIC else 0.0 if sig in _BENIGN else None
        if label is None:
            continue
        try:
            out[_key(r["Chromosome"], r["PositionVCF"], r["ReferenceAlleleVCF"], r["AlternateAlleleVCF"])] = label
        except KeyError:
            continue
    return out


def load_alphamissense(path: str | Path) -> dict[_VariantKey, float]:
    """{variant key: am_pathogenicity ∈ [0,1]} (higher = more pathogenic)."""
    out: dict[_VariantKey, float] = {}
    for r in _rows(path):
        try:
            out[_key(r["CHROM"], r["POS"], r["REF"], r["ALT"])] = float(r["am_pathogenicity"])
        except (KeyError, ValueError):
            continue
    return out


def load_esm1v(path: str | Path) -> dict[_VariantKey, float]:
    """{variant key: ESM1v masked-marginal LLR} (lower = more deleterious; negated at alignment time)."""
    out: dict[_VariantKey, float] = {}
    for r in _rows(path):
        try:
            out[_key(r["chrom"], r["pos"], r["ref"], r["alt"])] = float(r["esm1v"])
        except (KeyError, ValueError):
            continue
    return out


def align_scores(
    clinvar: dict[_VariantKey, float],
    alphamissense: dict[_VariantKey, float],
    esm1v: dict[_VariantKey, float],
) -> tuple[list[_VariantKey], list[float], list[float], list[float]]:
    """Inner-join the three tables on the variant key (deterministic sort). Returns
    ``(keys, labels, am_scores, esm_scores)`` — ESM1v LLR NEGATED so higher = more pathogenic, matching
    AlphaMissense's direction (so both predictors' errors are on the same footing)."""
    keys = sorted(set(clinvar) & set(alphamissense) & set(esm1v))
    labels = [clinvar[k] for k in keys]
    am_scores = [alphamissense[k] for k in keys]
    esm_scores = [-esm1v[k] for k in keys]
    return keys, labels, am_scores, esm_scores


def run_adapter_independence_live(
    data_dir: str | Path,
    *,
    am_threshold: float = 0.5,   # AlphaMissense pathogenic cutoff (published default ~0.564; 0.5 here)
    esm_threshold: float = 0.0,  # on the NEGATED LLR (deleterious -> positive)
) -> IndependenceReport:
    """Load + align the three real tables and compute the error-correlation report (C1). Data-gated:
    raises FileNotFoundError if any file is absent. Thresholds are simple defaults — calibrating each
    on a held-out split (per the plan) is a refinement; the report is honest either way."""
    d = Path(data_dir)

    def _one(stem: str):
        hits = sorted(d.glob(f"{stem}.tsv")) + sorted(d.glob(f"{stem}.tsv.gz"))
        if not hits:
            raise FileNotFoundError(f"no {stem}.tsv[.gz] under {d}")
        return hits[0]

    clinvar = load_clinvar_labels(_one("clinvar_variant_summary"))
    am = load_alphamissense(_one("AlphaMissense_hg38"))
    esm = load_esm1v(_one("esm1v_llr"))
    _keys, labels, am_scores, esm_scores = align_scores(clinvar, am, esm)
    return independence_report(am_scores, esm_scores, labels, threshold_a=am_threshold, threshold_b=esm_threshold)
