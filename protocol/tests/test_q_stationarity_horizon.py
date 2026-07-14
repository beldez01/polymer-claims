"""neg-whisper ④ — stationarity horizon on the calibration `q`.

Additive optional fields on CalibrationReport + a pure `stamp_stationarity`. UNSET => byte-identical
to the pre-field report (the certificate is unchanged), covered by the drop-when-unset serializer and
the unchanged existing calibration suite.
"""
from __future__ import annotations

import json

from polymer_protocol.calibration import (
    CalibrationReport,
    TierStat,
    stamp_stationarity,
)


def _report() -> CalibrationReport:
    z = TierStat(n_total=0, n_failed=0)
    return CalibrationReport(target_q=0.05, definitional=z, anchored=z, attested=z)


def test_unstamped_report_serializes_without_horizon_keys():
    d = json.loads(_report().model_dump_json())
    assert "validity_frontier" not in d  # byte-identical to pre-④ (no new key)
    assert "as_of_current" not in d


def test_stamp_sets_frontier_and_current_when_nothing_drifted():
    r = stamp_stationarity(_report(), frontier=("sha256:bbb", "sha256:aaa"))
    assert r.validity_frontier == ("sha256:aaa", "sha256:bbb")  # sorted, deterministic
    assert r.as_of_current is True
    d = json.loads(r.model_dump_json())
    assert d["validity_frontier"] == ["sha256:aaa", "sha256:bbb"]
    assert d["as_of_current"] is True


def test_drift_on_a_constituent_marks_q_expired_not_wrong():
    r = stamp_stationarity(
        _report(), frontier=("sha256:aaa", "sha256:bbb"), drifted=("sha256:bbb",)
    )
    assert r.as_of_current is False  # a watched hash drifted -> q expired (stale, not wrong)
    assert r.validity_frontier == ("sha256:aaa", "sha256:bbb")  # the frontier itself is retained


def test_empty_frontier_makes_no_stationarity_claim():
    r = stamp_stationarity(_report(), frontier=())
    assert r.validity_frontier == ()
    assert r.as_of_current is None
    # unchanged -> still serializes without the horizon keys (byte-identical)
    assert "as_of_current" not in json.loads(r.model_dump_json())


def test_stamped_report_round_trips():
    r = stamp_stationarity(_report(), frontier=("sha256:x",), drifted=())
    again = CalibrationReport.model_validate_json(r.model_dump_json())
    assert again.validity_frontier == ("sha256:x",)
    assert again.as_of_current is True
