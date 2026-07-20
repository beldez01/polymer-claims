"""C4 — Leg B independent senseability tier classifier.

Two levels:
  1. Self-contained contract checks (no SensorKit) — Leg B stands alone.
  2. Agreement: over thousands of random variants, Leg B must return the EXACT tier
     SensorKit's classify_variant (Leg A) returns. This is the REPRODUCED evidence —
     two independent code paths agreeing (BRIDGE-SENSORKIT-CLAIMS-SPEC §4). Skips
     cleanly if SensorKit isn't importable in this env.
"""
import random

import pytest

from polymer_claims.sensor_senseability_reimpl import (
    reimpl_classify_variant,
    reimpl_tier_ordinal,
    TIER_ORDINAL,
)


def test_ideal_when_variant_creates_cca_at_site():
    # variant at index 5 turns wt "CAA" register into mut "CCA" (productivity 1.0), d=0
    wt = "AAAACAAAAAAA"
    mut = "AAAACCAAAAAA"
    assert reimpl_classify_variant(wt, mut, 5) == "ideal"
    assert reimpl_tier_ordinal(wt, mut, 5) == TIER_ORDINAL["ideal"] == 3


def test_unsenseable_when_no_editable_site():
    wt = "AAAAAGAAAAAA"
    mut = "AAAAAAAAAAAA"  # no C middle base anywhere -> no register
    assert reimpl_classify_variant(wt, mut, 5) == "unsenseable"
    assert reimpl_tier_ordinal(wt, mut, 5) == 0


def test_ordinal_is_monotone():
    assert TIER_ORDINAL == {"unsenseable": 0, "engineered": 1, "good": 2, "ideal": 3}


def test_agreement_with_sensorkit_over_random_panel():
    """The load-bearing REPRODUCED check: Leg B == Leg A (SensorKit) on the exact tier."""
    pytest.importorskip("sensorkit")
    from sensorkit.records import Variant
    from sensorkit.screen import classify_variant

    rng = random.Random(20260720)  # deterministic
    bases = "ACGU"
    mismatches = []
    n_checked = 0
    for _ in range(4000):
        length = rng.randint(18, 60)
        wt = "".join(rng.choice(bases) for _ in range(length))
        vi = rng.randint(2, length - 3)
        alt = rng.choice([b for b in bases if b != wt[vi]])
        mut = wt[:vi] + alt + wt[vi + 1:]
        for md in (2, 3):
            leg_a = classify_variant(
                Variant(gene="x", name="x", hgvs_c="", window_wt=wt,
                        window_mut=mut, var_index=vi, tpm=1.0),
                md,
            )
            leg_b = reimpl_classify_variant(wt, mut, vi, md)
            n_checked += 1
            if leg_a != leg_b:
                mismatches.append((wt, mut, vi, md, leg_a, leg_b))

    assert not mismatches, (
        f"{len(mismatches)}/{n_checked} tier disagreements, e.g. {mismatches[:3]}"
    )
