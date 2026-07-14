"""Adapter-independence loader (C1 live-run data path) — parsing tested on a tiny committed fixture.

The real ClinVar/AlphaMissense/ESM1v files are gitignored; the live run is skipif-guarded and executes
only when the operator drops them into data/adapter_independence/. Never fabricates scores.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from polymer_claims.adapter_independence_data import (
    align_scores,
    load_alphamissense,
    load_clinvar_labels,
    load_esm1v,
    run_adapter_independence_live,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "adapter_independence"
_REAL = Path(__file__).parent.parent / "data" / "adapter_independence"


def test_clinvar_labels_filter_assembly_type_and_significance():
    labels = load_clinvar_labels(_FIXTURE / "clinvar_variant_summary.tsv")
    # GRCh38 SNVs with a clear significance only: v1/v2/v3 kept; VUS (v4) + the GRCh37 row dropped
    assert labels == {
        ("1", "100", "A", "T"): 1.0,   # Pathogenic
        ("1", "200", "C", "G"): 0.0,   # Benign
        ("2", "300", "G", "A"): 1.0,   # Likely pathogenic
    }


def test_alphamissense_and_esm1v_parse_with_normalized_keys():
    am = load_alphamissense(_FIXTURE / "AlphaMissense_hg38.tsv")   # 'chr' prefix stripped
    esm = load_esm1v(_FIXTURE / "esm1v_llr.tsv")
    assert am[("1", "100", "A", "T")] == 0.95
    assert esm[("2", "300", "G", "A")] == -4.0


def test_align_inner_joins_and_negates_esm_llr():
    clinvar = load_clinvar_labels(_FIXTURE / "clinvar_variant_summary.tsv")
    am = load_alphamissense(_FIXTURE / "AlphaMissense_hg38.tsv")
    esm = load_esm1v(_FIXTURE / "esm1v_llr.tsv")
    keys, labels, am_scores, esm_scores = align_scores(clinvar, am, esm)
    assert keys == [("1", "100", "A", "T"), ("1", "200", "C", "G"), ("2", "300", "G", "A")]
    assert labels == [1.0, 0.0, 1.0]
    assert am_scores == [0.95, 0.10, 0.80]
    assert esm_scores == [5.0, 0.5, 4.0]  # ESM1v LLR negated -> higher = more pathogenic


def test_run_on_fixture_dir_produces_a_report():
    rep = run_adapter_independence_live(_FIXTURE)
    assert rep.n == 3
    assert not math.isnan(rep.rho)  # 3 aligned variants -> a defined error-correlation


def test_missing_files_raise_not_fabricate(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_adapter_independence_live(tmp_path)  # empty dir -> honest failure, never fabricated scores


@pytest.mark.skipif(
    not (_REAL.exists() and any(_REAL.glob("clinvar_variant_summary.tsv*"))),
    reason="drop real ClinVar + AlphaMissense + ESM1v into data/adapter_independence/ to run the live experiment",
)
def test_adapter_independence_live_real_data():
    rep = run_adapter_independence_live(_REAL)
    assert rep.n > 0
    assert -1.0 <= rep.rho <= 1.0
    # the headline: N_eff = 2/(1+rho). rho~0 -> ~2 independent witnesses; rho->1 -> ~1 (they fail together).
    print(f"REAL adapter-independence: N={rep.n} rho={rep.rho:.4f} N_eff={rep.n_eff:.3f} "
          f"confusion(both_ok={rep.both_correct}, a_only={rep.a_only_correct}, "
          f"b_only={rep.b_only_correct}, both_wrong={rep.both_wrong})")
