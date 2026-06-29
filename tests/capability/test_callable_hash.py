"""Tests for implementation_hash_for_callable (Sub-task A, Task 12)."""
from __future__ import annotations

import re


from polymer_claims.adapter_identity import (
    implementation_hash_for_callable,
    implementation_hash_for_adapter,
)
from polymer_claims.benchmark_adapter import FixtureModelAdapter, FixtureBaselineAdapter
from polymer_claims.benchmark_evidence import score_advantage, paired_advantage_evalue
from polymer_claims.exec_adapters import StatsPureAdapter

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# implementation_hash_for_callable — format
# ---------------------------------------------------------------------------


def test_callable_hash_format_on_predict():
    fn = FixtureModelAdapter.predict
    h = implementation_hash_for_callable(fn)
    assert _SHA256_RE.match(h), f"unexpected format: {h!r}"


def test_callable_hash_format_on_score_advantage():
    h = implementation_hash_for_callable(score_advantage)
    assert _SHA256_RE.match(h), f"unexpected format: {h!r}"


def test_callable_hash_format_on_paired_advantage_evalue():
    h = implementation_hash_for_callable(paired_advantage_evalue)
    assert _SHA256_RE.match(h), f"unexpected format: {h!r}"


# ---------------------------------------------------------------------------
# implementation_hash_for_callable — stability
# ---------------------------------------------------------------------------


def test_callable_hash_is_stable_for_model_predict():
    fn = FixtureModelAdapter.predict
    assert implementation_hash_for_callable(fn) == implementation_hash_for_callable(fn)


def test_callable_hash_is_stable_for_baseline_predict():
    fn = FixtureBaselineAdapter.predict
    assert implementation_hash_for_callable(fn) == implementation_hash_for_callable(fn)


def test_callable_hash_is_stable_for_score_advantage():
    assert (
        implementation_hash_for_callable(score_advantage)
        == implementation_hash_for_callable(score_advantage)
    )


def test_callable_hash_is_stable_for_paired_advantage_evalue():
    assert (
        implementation_hash_for_callable(paired_advantage_evalue)
        == implementation_hash_for_callable(paired_advantage_evalue)
    )


# ---------------------------------------------------------------------------
# implementation_hash_for_callable — distinctness (swapping changes the hash)
# ---------------------------------------------------------------------------


def test_model_predict_differs_from_baseline_predict():
    h_model = implementation_hash_for_callable(FixtureModelAdapter.predict)
    h_baseline = implementation_hash_for_callable(FixtureBaselineAdapter.predict)
    assert h_model != h_baseline


def test_predict_differs_from_score_advantage():
    h_predict = implementation_hash_for_callable(FixtureModelAdapter.predict)
    h_scorer = implementation_hash_for_callable(score_advantage)
    assert h_predict != h_scorer


def test_score_advantage_differs_from_evalue_transform():
    h_scorer = implementation_hash_for_callable(score_advantage)
    h_transform = implementation_hash_for_callable(paired_advantage_evalue)
    assert h_scorer != h_transform


def test_all_four_callables_have_distinct_hashes():
    hashes = [
        implementation_hash_for_callable(FixtureModelAdapter.predict),
        implementation_hash_for_callable(FixtureBaselineAdapter.predict),
        implementation_hash_for_callable(score_advantage),
        implementation_hash_for_callable(paired_advantage_evalue),
    ]
    assert len(set(hashes)) == 4, f"expected 4 distinct hashes, got {hashes}"


# ---------------------------------------------------------------------------
# implementation_hash_for_callable — altering a callable changes the hash
# ---------------------------------------------------------------------------


def test_different_lambda_same_code_structure_different_qualname():
    """Two functions with the same body but different qualnames produce different hashes."""
    def fn_a(x):
        return x

    def fn_b(x):
        return x

    # fn_a and fn_b have the same bytecode structure but different qualnames
    h_a = implementation_hash_for_callable(fn_a)
    h_b = implementation_hash_for_callable(fn_b)
    # qualnames differ ("fn_a" vs "fn_b"), so hashes should differ
    assert h_a != h_b


# ---------------------------------------------------------------------------
# implementation_hash_for_adapter — refactored to delegate (no behavior change)
# ---------------------------------------------------------------------------


class _DummyAdapter:
    """Minimal adapter with an execute method for hash testing."""

    def execute(self, node, upstream, ctx):
        return None

    def predict(self, examples):
        return None


def test_adapter_hash_format():
    h = implementation_hash_for_adapter(_DummyAdapter())
    assert _SHA256_RE.match(h), f"unexpected format: {h!r}"


def test_adapter_hash_is_stable():
    adapter = _DummyAdapter()
    h1 = implementation_hash_for_adapter(adapter)
    h2 = implementation_hash_for_adapter(adapter)
    assert h1 == h2


def test_adapter_hash_works_with_class():
    h_instance = implementation_hash_for_adapter(_DummyAdapter())
    h_class = implementation_hash_for_adapter(_DummyAdapter)
    assert h_instance == h_class


def test_adapter_hash_does_not_equal_callable_hash_of_execute():
    """implementation_hash_for_adapter uses the *class* module.qualname as identity,
    while implementation_hash_for_callable uses the method's own module.qualname.
    They share the same byte-hashing core but produce different digests for the same
    execute method — this is intentional to preserve pre-Task-12 adapter hash values."""
    h_adapter = implementation_hash_for_adapter(_DummyAdapter)
    h_execute = implementation_hash_for_callable(_DummyAdapter.execute)
    assert h_adapter != h_execute, (
        "adapter hash must use class identity, not method qualname"
    )


# ---------------------------------------------------------------------------
# Regression pin — backward-compat guard for pre-Task-12 adapter hash values
# ---------------------------------------------------------------------------


def test_stats_pure_adapter_hash_is_pinned():
    """Regression pin: StatsPureAdapter must hash to the pre-Task-12 value.

    This value was produced by the original implementation_hash_for_adapter before
    Task 12 introduced implementation_hash_for_callable.  Any change here means the
    adapter independence check in the protocol registry will reject previously
    attested adapters — change only if you intend a breaking migration.

    Pin value: sha256:ff14cf51ba2917fb9033976db374a80992b3956d182ac53448946e346f0077a5
    """
    expected = "sha256:ff14cf51ba2917fb9033976db374a80992b3956d182ac53448946e346f0077a5"
    assert implementation_hash_for_adapter(StatsPureAdapter) == expected, (
        "StatsPureAdapter hash changed — this breaks backward-compat with "
        "pre-Task-12 attestation goldens.  Update only via a deliberate migration."
    )
