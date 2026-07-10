import statistics
from polymer_claims.exec_adapters import (
    StatsPureAdapter, HodgesLehmannMeanDiffAdapter, immuno_independent_registry,
)

class _Node:
    """Minimal stand-in exposing the two groups the way _resolve reads them."""
    def __init__(self, a, b): self.groups = (a, b)

def _hl(a, b):
    diffs = sorted(x - y for x in a for y in b)
    return statistics.median(diffs)

def test_hl_leg_matches_mean_on_symmetric_data(monkeypatch):
    a = [0.80, 0.82, 0.78]; b = [0.20, 0.18, 0.22]
    monkeypatch.setattr("polymer_claims.exec_adapters._resolve", lambda node: node.groups)
    node = _Node(a, b)
    mean = StatsPureAdapter().execute(node, (), None).value
    hl = HodgesLehmannMeanDiffAdapter().execute(node, (), None).value
    assert mean == __import__("pytest").approx(0.60, abs=0.02)
    assert hl == __import__("pytest").approx(0.60, abs=0.02)   # agree on real signal

def test_hl_leg_diverges_from_mean_on_skewed_outlier(monkeypatch):
    # one outlier drags the parametric mean but not the rank-based HL estimate:
    a = [0.50, 0.50, 0.50]; b = [0.10, 0.10, 100.0]
    monkeypatch.setattr("polymer_claims.exec_adapters._resolve", lambda node: node.groups)
    node = _Node(a, b)
    mean = StatsPureAdapter().execute(node, (), None).value      # ~ 0.50 - 33.4 << 0
    hl = HodgesLehmannMeanDiffAdapter().execute(node, (), None).value  # ~ +0.40
    assert mean < -10.0
    assert hl > 0.0
    assert (mean > 0) != (hl > 0)   # legs DISAGREE in direction -> AGREE check fails -> no license

def test_registry_names_the_two_independent_legs():
    reg = immuno_independent_registry()
    ids = tuple(c.identity for c in reg.credentials)
    assert ids == ("stats-pure", "meandiff-hodges-lehmann")
    owners = {c.owner for c in reg.credentials}
    assert len(owners) == 2   # distinct owners (air-gap requirement)
