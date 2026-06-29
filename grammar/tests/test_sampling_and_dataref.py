"""TDD: SamplingRegime + DataRefKind.BENCHMARK — Task 3."""
from __future__ import annotations

from polymer_grammar import DataRefKind, data_ref_ok
from polymer_grammar.sampling import SamplingRegime


# ---------------------------------------------------------------------------
# SamplingRegime
# ---------------------------------------------------------------------------

def test_sampling_regime_iid_value():
    assert SamplingRegime.IID_EXAMPLES.value == "iid_examples"


def test_sampling_regime_is_str():
    assert isinstance(SamplingRegime.IID_EXAMPLES, str)


# ---------------------------------------------------------------------------
# DataRefKind.BENCHMARK — canonical format: bench:sha256:<64 hex chars>
# ---------------------------------------------------------------------------

_GOOD_HASH = "a" * 64  # 64 lowercase hex chars


def test_benchmark_valid():
    assert data_ref_ok(DataRefKind.BENCHMARK, f"bench:sha256:{_GOOD_HASH}") is True


def test_benchmark_bare_hex_rejected():
    """bench:<hex> without sha256: prefix is not valid."""
    assert data_ref_ok(DataRefKind.BENCHMARK, f"bench:{_GOOD_HASH}") is False


def test_benchmark_se_ref_rejected():
    assert data_ref_ok(DataRefKind.BENCHMARK, "se:x@1") is False


def test_benchmark_opaque_rejected():
    assert data_ref_ok(DataRefKind.BENCHMARK, "some-opaque-string") is False


def test_benchmark_empty_rejected():
    assert data_ref_ok(DataRefKind.BENCHMARK, "") is False


def test_benchmark_wrong_hash_length():
    assert data_ref_ok(DataRefKind.BENCHMARK, f"bench:sha256:{'a' * 63}") is False
    assert data_ref_ok(DataRefKind.BENCHMARK, f"bench:sha256:{'a' * 65}") is False


def test_benchmark_uppercase_hex_rejected():
    """Must be lowercase hex per canonical form."""
    assert data_ref_ok(DataRefKind.BENCHMARK, f"bench:sha256:{'A' * 64}") is False


# ---------------------------------------------------------------------------
# Sanity: existing kinds still work
# ---------------------------------------------------------------------------

def test_opaque_sanity():
    assert data_ref_ok(DataRefKind.OPAQUE, "any-non-empty-string") is True
    assert data_ref_ok(DataRefKind.OPAQUE, "") is False


def test_se_contract_sanity():
    assert data_ref_ok(DataRefKind.SE_CONTRACT, "se:my-contract@1") is True
    assert data_ref_ok(DataRefKind.SE_CONTRACT, "se:x@1") is True
    assert data_ref_ok(DataRefKind.SE_CONTRACT, "opaque-garbage") is False
