from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_claims.contracts import AccessMethod, Checksum, SEContractRef


def _ref(**kw) -> SEContractRef:
    base = dict(
        contract_uid="tet2_epicv2_demo@1",
        dimnames_hash="sha256:" + "0" * 64,
        assay="beta",
        selection=(("group_col", "Sample_Group"),),
        genome_assembly="hg38",
        self_uri="drs://local/tet2_epicv2_demo@1",
        size=123,
        checksums=(Checksum(checksum="ab" * 32),),
        access_methods=(AccessMethod(type="file", access_url="/x/y.tsv"),),
    )
    base.update(kw)
    return SEContractRef(**base)


def test_se_contract_ref_round_trips():
    ref = _ref()
    again = SEContractRef.model_validate(ref.model_dump(mode="json"))
    assert again == ref
    assert again.refget_digest is None  # noted-but-empty slot


def test_se_contract_ref_is_frozen():
    ref = _ref()
    with pytest.raises(ValidationError):
        ref.assay = "counts"  # frozen models reject mutation
