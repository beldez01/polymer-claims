from __future__ import annotations

import subprocess
import sys

from polymer_grammar import Status

from polymer_claims.methyl_adapters import region_delta_beta_claim
from tests.conftest import methyl_node

_POWERED = "se:epicv2_casectrl_powered@1"
_STRONG = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_WEAK = ("cg00000006", "cg00000007", "cg00000008", "cg00000009", "cg00000010")


def _node(region_probes, **kw):
    claim = region_delta_beta_claim("c-x", ref=_POWERED, region_probes=region_probes, threshold=0.10)
    r = methyl_node(claim=claim, **kw)
    for _ in range(3):
        r.tick()
    return r


def test_egate_licenses_strong_region_live():
    r = _node(_STRONG, evalue_gate=True)
    c = next(x for x in r.corpus.claims if x.id == "c-x")
    assert c.status == Status.LICENSED
    assert r.corpus.fdr_ledger.n_discoveries == 1


def test_egate_blocks_weak_region_live():
    r = _node(_WEAK, evalue_gate=True)
    c = next(x for x in r.corpus.claims if x.id == "c-x")
    assert c.status != Status.LICENSED
    assert r.corpus.fdr_ledger.n_discoveries == 0


def test_weak_region_licenses_without_egate():
    r = _node(_WEAK, evalue_gate=False)
    c = next(x for x in r.corpus.claims if x.id == "c-x")
    assert c.status == Status.LICENSED


def test_weak_claim_not_re_tested_across_ticks():
    # the weak claim lingers PENDING across 3 ticks; it must be e-tested ONCE, not once-per-tick.
    r = _node(_WEAK, evalue_gate=True)
    assert r.corpus.fdr_ledger.n_tests == 1
    assert r.corpus.fdr_ledger.n_discoveries == 0


def test_node_import_stays_numpy_free():
    code = ("import polymer_claims.node, sys; "
            "assert 'numpy' not in sys.modules, sorted(m for m in sys.modules if 'numpy' in m)")
    subprocess.run([sys.executable, "-c", code], check=True)
