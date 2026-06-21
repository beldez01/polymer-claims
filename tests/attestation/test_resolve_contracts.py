from __future__ import annotations

from polymer_claims.attestation import resolve_contract_index
from polymer_claims.contracts import AccessMethod, Checksum, SEContractRef
from tests.attestation._fixtures import corpus_with


def _ref(h: str, uid: str) -> SEContractRef:
    return SEContractRef(
        contract_uid=uid,
        dimnames_hash=h,
        assay="meth",
        genome_assembly="GRCh38",
        self_uri=f"drs://local/{uid}",
        size=10,
        checksums=(Checksum(checksum="f" * 64),),
        access_methods=(AccessMethod(type="file", access_url="/tmp/x"),),
    )


def test_extra_contracts_indexed_by_dimnames_hash():
    h = "sha256:" + "e" * 64
    idx = resolve_contract_index(corpus_with(), extra=(_ref(h, "ds-extra"),))
    assert idx[h].contract_uid == "ds-extra"


def test_resolver_never_crashes_and_returns_dict():
    # Bundled manifests are loaded best-effort; the call must always return a dict.
    idx = resolve_contract_index(corpus_with())
    assert isinstance(idx, dict)
