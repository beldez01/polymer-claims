"""Polymer bundle (Sigstore-INSPIRED, not wire-compatible — see spec §4.4): a signed DSSE envelope +
its inclusion proof + signed checkpoint, verifiable fully offline against PINNED keys.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum

from polymer_claims import signing
from polymer_claims import transparency as T
from polymer_claims.attestation import DsseEnvelope

MEDIA_TYPE = "application/vnd.polymer.bundle.v0.1+json"


class TrustStatus(str, Enum):
    TRUSTED_VALID = "trusted_valid"
    STRUCTURALLY_VALID_UNTRUSTED = "structurally_valid_untrusted"
    INVALID = "invalid"


@dataclass(frozen=True)
class BundleVerification:
    status: TrustStatus
    envelope_signature_ok: bool
    inclusion_ok: bool
    checkpoint_signature_ok: bool
    signing_key_pinned: bool
    log_key_pinned: bool
    reason: str


def build_bundle(env: DsseEnvelope, signing_public_key, log_entry: T.LogEntry, log_public_key) -> dict:
    """Assemble a Polymer bundle. Enforces (spec finding-6) that the envelope carries exactly one
    signature whose keyid == keyid_for(signing_public_key); else ValueError."""
    expected_kid = signing.keyid_for(signing_public_key)
    if len(env.signatures) != 1 or env.signatures[0].keyid != expected_kid:
        raise ValueError(
            "build_bundle: envelope must carry exactly one signature whose keyid matches the "
            f"verification key ({expected_kid!r})"
        )
    fields = T.parse_checkpoint(log_entry.checkpoint)
    return {
        "mediaType": MEDIA_TYPE,
        "$schemaNote": "Sigstore-inspired layout; not wire-compatible with dev.sigstore.bundle. See spec §4.4.",
        "verificationMaterial": {
            "signingKey": {
                "rawBytesDER": base64.b64encode(signing.serialize_public_der(signing_public_key)).decode("ascii"),
                "keyHint": expected_kid,
            },
            "logKey": {
                "rawBytesDER": base64.b64encode(signing.serialize_public_der(log_public_key)).decode("ascii"),
                "keyHint": signing.keyid_for(log_public_key),
            },
            "inclusion": {
                "logIndex": log_entry.log_index,
                "logId": log_entry.log_id,
                "kindVersion": log_entry.kind_version,
                "integratedTime": log_entry.integrated_time,
                "treeSize": fields.tree_size,
                "rootHashHex": fields.root_hash.hex(),
                "hashesHex": list(log_entry.inclusion_proof),
                "checkpoint": log_entry.checkpoint,
            },
        },
        "dsseEnvelope": {
            "payloadType": env.payload_type,
            "payload": env.payload,
            "signatures": [{"sig": s.sig, "keyid": s.keyid} for s in env.signatures],
        },
    }


def _fail(reason: str, **flags) -> BundleVerification:
    base = dict(envelope_signature_ok=False, inclusion_ok=False, checkpoint_signature_ok=False,
                signing_key_pinned=False, log_key_pinned=False)
    base.update(flags)
    return BundleVerification(status=TrustStatus.INVALID, reason=reason, **base)


def verify_bundle(bundle: dict, *, signing_trust_key=None, log_trust_key=None) -> BundleVerification:
    """Trust-gated offline verifier. Never raises. rc-mapping is the CLI's job; this returns status."""
    try:
        if not isinstance(bundle, dict) or bundle.get("mediaType") != MEDIA_TYPE:
            return _fail(f"wrong or missing mediaType (expected {MEDIA_TYPE})")
        vm = bundle["verificationMaterial"]
        inc = vm["inclusion"]
        env = DsseEnvelope.model_validate(bundle["dsseEnvelope"])
        embedded_sig_der = base64.b64decode(vm["signingKey"]["rawBytesDER"], validate=True)
        embedded_log_der = base64.b64decode(vm["logKey"]["rawBytesDER"], validate=True)
    except Exception as exc:                       # noqa: BLE001 - never raise on malformed input
        return _fail(f"malformed bundle: {exc}")

    # Trust pinning: a supplied key that does not match the embedded material is a hard INVALID.
    signing_key_pinned = False
    log_key_pinned = False
    try:
        if signing_trust_key is not None:
            if signing.serialize_public_der(signing_trust_key) != embedded_sig_der:
                return _fail("signing key mismatch: pinned key does not match bundle material")
            signing_key_pinned = True
        if log_trust_key is not None:
            if signing.serialize_public_der(log_trust_key) != embedded_log_der:
                return _fail("log key mismatch: pinned key does not match bundle material",
                             signing_key_pinned=signing_key_pinned)
            log_key_pinned = True
        signing_pub = signing.load_public_der(embedded_sig_der)
        log_pub = signing.load_public_der(embedded_log_der)
    except Exception as exc:                       # noqa: BLE001
        return _fail(f"key load failed: {exc}", signing_key_pinned=signing_key_pinned,
                     log_key_pinned=log_key_pinned)

    # (1) DSSE signature over the envelope.
    env_ok = signing.verify_envelope(env, signing_pub)
    # (2) Inclusion metadata is semantically authenticated against the log key + accepted for local.
    metadata_ok = False
    # (3) Inclusion proof recomputes to the checkpoint root at logIndex/treeSize.
    inclusion_ok = False
    # (4) Checkpoint signature vs the log key.
    ckpt_ok = False
    try:
        metadata_ok = (
            inc.get("logId") == signing.keyid_for(log_pub)         # logId binds to the actual log key
            and inc.get("kindVersion") == T.LOCAL_KIND_VERSION      # accepted kind for a local bundle
            and inc.get("integratedTime") is None                   # local v1 has no integrated time
        )
        fields = T.parse_checkpoint(inc["checkpoint"])
        leaf = T.leaf_hash(T.canonical_entry_bytes(env))
        proof = [bytes.fromhex(h) for h in inc["hashesHex"]]
        inclusion_ok = (
            fields.root_hash.hex() == inc["rootHashHex"]
            and fields.tree_size == inc["treeSize"]
            and T.verify_inclusion(leaf, inc["logIndex"], inc["treeSize"], proof, fields.root_hash)
        )
        ckpt_ok = T.verify_checkpoint(inc["checkpoint"], log_pub)
    except Exception:                              # noqa: BLE001
        inclusion_ok = False

    if not (env_ok and metadata_ok and inclusion_ok and ckpt_ok):
        if not env_ok:
            failing = "envelope signature"
        elif not metadata_ok:
            failing = "inclusion metadata (logId/kindVersion/integratedTime)"
        elif not inclusion_ok:
            failing = "inclusion proof"
        else:
            failing = "checkpoint signature"
        return BundleVerification(
            status=TrustStatus.INVALID, envelope_signature_ok=env_ok, inclusion_ok=inclusion_ok,
            checkpoint_signature_ok=ckpt_ok, signing_key_pinned=signing_key_pinned,
            log_key_pinned=log_key_pinned, reason=f"{failing} verification failed",
        )
    # TRUSTED_VALID requires BOTH the signer identity AND the log trust root to be pinned and matched;
    # one alone leaves the other merely bundle-embedded (not trusted).
    status = TrustStatus.TRUSTED_VALID if (signing_key_pinned and log_key_pinned) \
        else TrustStatus.STRUCTURALLY_VALID_UNTRUSTED
    reason = "" if status == TrustStatus.TRUSTED_VALID \
        else "both --pub-key and --log-pub-key must be pinned for trust (structurally valid only)"
    return BundleVerification(
        status=status, envelope_signature_ok=True, inclusion_ok=True, checkpoint_signature_ok=True,
        signing_key_pinned=signing_key_pinned, log_key_pinned=log_key_pinned, reason=reason,
    )
