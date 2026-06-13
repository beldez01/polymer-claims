# protocol/tests/test_elond_fdr_control.py
"""Headline rigor deliverable: e-LOND controls FDR under dependence in a regime where it MATTERS —
a naive fixed-threshold procedure (no online γ_t·(D+1) discount) breaches the ceiling, e-LOND holds."""
from __future__ import annotations

import math
import random

from polymer_grammar.fdr import FDRLedger, process_stream


def _null_evalue(z: float, lam: float = 2.0) -> float:
    # e = exp(lam*z - lam^2/2): valid e-value (E[e]=1) for z ~ N(0,1) under the null. lam=2 gives a
    # heavier tail so nulls occasionally cross the bar -> real FDR pressure to control.
    return math.exp(lam * z - 0.5 * lam * lam)


def _stream(rng, m, pi0, shift):
    shared = rng.gauss(0.0, 1.0)                    # SHARED latent factor -> dependence
    items, truth = [], {}
    for i in range(m):
        is_null = rng.random() < pi0
        z = 0.6 * shared + 0.8 * rng.gauss(0.0, 1.0)
        if not is_null:
            z += shift
        cid = f"h{i}"
        items.append((cid, _null_evalue(z)))
        truth[cid] = is_null
    return items, truth


def _fdp(discoveries, truth):
    d = list(discoveries)
    if not d:
        return 0.0
    return sum(1 for cid in d if truth[cid]) / len(d)


def test_elond_controls_fdr_where_naive_breaches():
    rng = random.Random(20260612)
    target, m, pi0, shift, trials = 0.10, 200, 0.92, 1.6, 400
    elond_fdps, naive_fdps = [], []
    naive_bar = 1.0 / target                         # reject e >= 1/target, NO online discount
    for _ in range(trials):
        items, truth = _stream(rng, m, pi0, shift)
        led = process_stream(FDRLedger(target_fdr=target), items)
        elond_fdps.append(_fdp(led.discoveries, truth))
        naive_disc = [cid for cid, e in items if e >= naive_bar]
        naive_fdps.append(_fdp(naive_disc, truth))
    elond_fdr = sum(elond_fdps) / trials
    naive_fdr = sum(naive_fdps) / trials
    # 1) e-LOND controls FDR under dependence:
    assert elond_fdr <= target + 0.03, f"e-LOND FDR {elond_fdr} > target"
    # 2) the regime is non-trivial AND the discount is load-bearing: the naive fixed-bar procedure
    #    BREACHES the ceiling on the SAME streams (so the test would catch a discount regression).
    assert naive_fdr > target + 0.05, f"naive FDR {naive_fdr} did not breach (regime too easy)"
    # 3) e-LOND is strictly more disciplined than naive here:
    assert elond_fdr < naive_fdr
