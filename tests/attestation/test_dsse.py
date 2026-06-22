from __future__ import annotations
import ast
import base64
import json
import sys
from pathlib import Path

from polymer_claims.attestation import (
    DsseEnvelope, DsseSignature, dsse_envelope, build_attestation_statements,
)
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat


def _stmt():
    claim = licensed_claim("c1", licensing(sat(mc(dimnames_hash="sha256:" + "a" * 64))))
    return build_attestation_statements(corpus_with(claim), contract_index={})[0]


def test_dsse_envelope_shape_and_roundtrip():
    env = dsse_envelope(_stmt())
    assert isinstance(env, DsseEnvelope)
    assert env.payload_type == "application/vnd.in-toto+json"
    assert env.signatures == ()
    assert json.loads(base64.b64decode(env.payload)) == json.loads(
        _stmt().model_dump_json(by_alias=True, exclude_none=True))


def test_dsse_envelope_serializes_with_intoto_aliases_and_empty_sigs():
    obj = json.loads(dsse_envelope(_stmt()).model_dump_json(by_alias=True, exclude_none=True))
    assert obj["payloadType"] == "application/vnd.in-toto+json"
    assert obj["signatures"] == []
    assert isinstance(obj["payload"], str)


def test_dsse_signature_keyid_optional():
    assert DsseSignature(sig="x").keyid is None


def test_attestation_no_new_thirdparty_imports():
    """Dependency guard: attestation.py may import only stdlib + pydantic + internal packages."""
    src = (Path(__file__).parents[2] / "src" / "polymer_claims" / "attestation.py").read_text()
    mods: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    thirdparty = mods - set(sys.stdlib_module_names) - {"polymer_grammar", "polymer_protocol", "polymer_claims"}
    assert thirdparty <= {"pydantic"}, f"unexpected third-party imports: {thirdparty}"
