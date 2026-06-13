# tests/test_powered_fixture.py
from __future__ import annotations

import statistics as st

from polymer_grammar import Comparator

from polymer_claims.contracts import load_contract
from polymer_claims.evidence import betting_evalue
from polymer_claims.methyl_adapters import _region_group_means, region_delta_beta_claim

_REF = "se:epicv2_casectrl_powered@1"
_STRONG = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_WEAK = ("cg00000006", "cg00000007", "cg00000008", "cg00000009", "cg00000010")
_BAR = 1.0 / (0.05 * (6.0 / 3.141592653589793 ** 2))  # e-LOND bar for the 1st discovery, fdr=0.05 (~32.9)


def _ab(probes):
    g = region_delta_beta_claim("x", ref=_REF, region_probes=probes).evaluation_plan.graph
    term = next(n for n in g.nodes if n.id == g.terminal)
    return _region_group_means(term)


def test_powered_contract_resolves():
    assert load_contract(_REF).dimnames_hash.startswith("sha256:")


def test_strong_region_licenses_e_above_bar():
    a, b = _ab(_STRONG)
    d = st.mean(b) - st.mean(a)
    assert 0.24 < d < 0.36  # ~0.30 planted
    e = betting_evalue(a, b, threshold=0.10, comparator=Comparator.GT)
    assert e > 40.0, f"strong e={e} must clear the e-LOND bar {_BAR:.1f}"


def test_weak_region_satisfied_but_e_below_bar():
    a, b = _ab(_WEAK)
    d = st.mean(b) - st.mean(a)
    assert d > 0.10, f"weak region must be SATISFIED (point estimate {d} > 0.10)"  # satisfies the criterion
    assert d < 0.16  # ~0.12 planted
    e = betting_evalue(a, b, threshold=0.10, comparator=Comparator.GT)
    assert e < _BAR, f"weak e={e} must be BELOW the bar {_BAR:.1f} (point-significant but weak evidence)"
