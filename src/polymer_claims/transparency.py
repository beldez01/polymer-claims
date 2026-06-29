"""Local RFC-6962 Merkle inclusion log + C2SP signed checkpoint for Polymer bundles.

Merkle math and `canonical_entry_bytes` are pure stdlib (no crypto). The checkpoint signing/verify
and the local log reuse `signing._require_crypto()` so the base install stays crypto-free. v1 is a
Merkle *inclusion* log (no consistency proofs -> no verified append-only-ness); see
docs/superpowers/specs/2026-06-25-transparency-log-design.md.
"""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol

if TYPE_CHECKING:
    from polymer_claims.attestation import DsseEnvelope


# --- canonical leaf bytes -------------------------------------------------------------------------
def canonical_entry_bytes(env: DsseEnvelope) -> bytes:
    """Deterministic canonical JSON of the SIGNED envelope — the bytes that become a Merkle leaf.
    Both submit and verify derive the leaf from this single function (no re-serialization drift)."""
    obj = {
        "payloadType": env.payload_type,
        "payload": env.payload,
        "signatures": [{"sig": s.sig, "keyid": s.keyid} for s in env.signatures],
    }
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# --- RFC-6962 Merkle tree hash (SHA-256, domain-separated) ----------------------------------------
def leaf_hash(entry: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + entry).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _largest_pow2_below(n: int) -> int:
    """Largest power of two strictly less than n (n >= 2)."""
    k = 1
    while k << 1 < n:
        k <<= 1
    return k


def _root_of_hashes(hashes: list[bytes]) -> bytes:
    n = len(hashes)
    if n == 1:
        return hashes[0]
    k = _largest_pow2_below(n)
    return node_hash(_root_of_hashes(hashes[:k]), _root_of_hashes(hashes[k:]))


def merkle_root(leaves: list[bytes]) -> bytes:
    if not leaves:
        raise ValueError("merkle_root requires at least one leaf (empty tree unused in v1)")
    return _root_of_hashes([leaf_hash(d) for d in leaves])


def _proof_from_hashes(hashes: list[bytes], index: int) -> list[bytes]:
    n = len(hashes)
    if n == 1:
        return []
    k = _largest_pow2_below(n)
    if index < k:
        return _proof_from_hashes(hashes[:k], index) + [_root_of_hashes(hashes[k:])]
    return _proof_from_hashes(hashes[k:], index - k) + [_root_of_hashes(hashes[:k])]


def inclusion_proof(leaves: list[bytes], index: int) -> list[bytes]:
    if not 0 <= index < len(leaves):
        raise ValueError(f"index {index} out of range for {len(leaves)} leaves")
    return _proof_from_hashes([leaf_hash(d) for d in leaves], index)


def verify_inclusion(leaf: bytes, index: int, tree_size: int, proof: list[bytes], root: bytes) -> bool:
    """Recompute the root from (leaf, index, tree_size, proof) per RFC-6962 §2.1.1 and compare.
    Direction at each step is derived from index/size arithmetic (not stored in the proof). Never
    raises: any structural problem returns False."""
    try:
        if not 0 <= index < tree_size:
            return False
        fn = index
        sn = tree_size - 1        # canonical RFC-6962 audit-path algorithm uses tree_size - 1
        h = leaf
        for sibling in proof:
            if sn == 0:           # ran out of tree before the proof was exhausted
                return False
            if (fn & 1) or (fn == sn):
                h = node_hash(sibling, h)
                while fn and not (fn & 1):    # advance past trailing right-child levels
                    fn >>= 1
                    sn >>= 1
            else:
                h = node_hash(h, sibling)
            fn >>= 1
            sn >>= 1
        return sn == 0 and h == root
    except Exception:
        return False


# --- C2SP signed checkpoint -----------------------------------------------------------------------
_SIG_PREFIX = "— "  # C2SP note signature lines start with em-dash + space


@dataclass(frozen=True)
class CheckpointFields:
    origin: str
    tree_size: int
    root_hash: bytes
    timestamp: str


def format_checkpoint_body(origin: str, tree_size: int, root_hash: bytes, timestamp: str) -> str:
    """The signed C2SP note body: origin / tree_size / base64(root) / Timestamp lines, then a blank
    line that terminates the body (C2SP rule). The trailing blank line IS part of the signed bytes."""
    b64root = base64.b64encode(root_hash).decode("ascii")
    return f"{origin}\n{tree_size}\n{b64root}\nTimestamp: {timestamp}\n\n"


def _keyhint(origin: str, public_key) -> bytes:
    from polymer_claims.signing import serialize_public_der
    return hashlib.sha256(origin.encode("utf-8") + b"\n" + serialize_public_der(public_key)).digest()[:4]


def sign_checkpoint(origin: str, tree_size: int, root_hash: bytes, timestamp: str, log_private_key) -> str:
    from polymer_claims.signing import _require_crypto
    _require_crypto()  # raise the friendly [sign] error early if absent
    body = format_checkpoint_body(origin, tree_size, root_hash, timestamp)
    sig = log_private_key.sign(body.encode("utf-8"))
    hint = _keyhint(origin, log_private_key.public_key())
    blob = base64.b64encode(hint + sig).decode("ascii")
    return f"{body}{_SIG_PREFIX}{origin} {blob}\n"


def parse_checkpoint(note: str) -> CheckpointFields:
    lines = note.splitlines()
    if len(lines) < 5 or not lines[3].startswith("Timestamp: ") or lines[4] != "":
        raise ValueError("malformed checkpoint note (expected C2SP blank-line-terminated body)")
    return CheckpointFields(
        origin=lines[0],
        tree_size=int(lines[1]),
        root_hash=base64.b64decode(lines[2], validate=True),
        timestamp=lines[3][len("Timestamp: "):],
    )


def verify_checkpoint(note: str, log_public_key) -> bool:
    """True iff >=1 signature line verifies over the note body against log_public_key AND carries the
    expected 4-byte keyhint for that key/origin. Never raises on malformed input."""
    from polymer_claims.signing import _require_crypto
    _ed, _ser, InvalidSignature = _require_crypto()
    # Missing crypto intentionally raises ModuleNotFoundError(name="cryptography") here (mirrors
    # signing.verify_envelope) so the CLI surfaces the friendly [sign] install hint; "never raises"
    # is scoped to malformed INPUT (handled below), not a missing dependency.
    try:
        idx = note.index("\n" + _SIG_PREFIX)
    except ValueError:
        return False
    body_str = note[: idx + 1]
    if not body_str.endswith("\n\n"):        # C2SP: a blank line MUST terminate the signed body
        return False
    body = body_str.encode("utf-8")
    origin = note.split("\n", 1)[0]          # origin is the first body line (itself signed)
    expected_hint = _keyhint(origin, log_public_key)
    sig_block = note[idx + 1:]
    for line in sig_block.splitlines():
        if not line.startswith(_SIG_PREFIX):
            continue
        try:
            blob = base64.b64decode(line.rsplit(" ", 1)[1], validate=True)
            if blob[:4] != expected_hint:    # keyhint must match this key/origin
                continue
            log_public_key.verify(blob[4:], body)  # remaining bytes are the ed25519 signature
            return True
        except (ValueError, IndexError, TypeError, InvalidSignature):
            continue
    return False


# --- Log layer (LocalInclusionLog) ---------------------------------------------------------------

LOCAL_KIND_VERSION = "polymer-inclusion/0.1"


@dataclass(frozen=True)
class LogEntry:
    log_index: int
    inclusion_proof: list[str]      # hex sibling hashes
    checkpoint: str                 # C2SP signed-note string (state AFTER this entry)
    log_id: str
    integrated_time: str | None
    kind_version: str


class TransparencyLog(Protocol):
    def submit(self, entry_bytes: bytes) -> LogEntry: ...

    @property
    def public_key_pem(self) -> bytes: ...


class LocalInclusionLog:
    """Append-only Merkle inclusion log backed by entries.jsonl (base64 lines). Single-process,
    single-writer; no consistency proofs (not verified-append-only). The clock callable returns an
    RFC-3339 UTC string (injected for determinism)."""

    def __init__(self, log_dir, log_private_key, *, origin: str = "polymer-claims-local-log",
                 clock: Callable[[], str]):
        self._dir = Path(log_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "entries.jsonl"
        self._key = log_private_key
        self._origin = origin
        self._clock = clock

    def _load_leaves(self) -> list[bytes]:
        if not self._path.exists():
            return []
        leaves = []
        for line in self._path.read_text().splitlines():
            if line:
                leaves.append(base64.b64decode(line, validate=True))
        return leaves

    @property
    def public_key_pem(self) -> bytes:
        from polymer_claims.signing import serialize_public_pem
        return serialize_public_pem(self._key.public_key())

    def submit(self, entry_bytes: bytes) -> LogEntry:
        from polymer_claims.signing import keyid_for
        leaves = self._load_leaves()
        index = len(leaves)
        leaves.append(entry_bytes)
        # Compute + sign FIRST (all in-memory), then append the line LAST as the commit point: if
        # sign_checkpoint fails or the process dies before the write, no orphan line is persisted and
        # the index cannot drift on reopen.
        root = merkle_root(leaves)
        proof = inclusion_proof(leaves, index)
        checkpoint = sign_checkpoint(self._origin, len(leaves), root, self._clock(), self._key)
        with self._path.open("a") as fh:
            fh.write(base64.b64encode(entry_bytes).decode("ascii") + "\n")
        return LogEntry(
            log_index=index,
            inclusion_proof=[h.hex() for h in proof],
            checkpoint=checkpoint,
            log_id=keyid_for(self._key.public_key()),
            integrated_time=None,
            kind_version=LOCAL_KIND_VERSION,
        )
