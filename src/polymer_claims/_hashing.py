"""The single canonical content-address primitive for the umbrella package.

Sorted-keys / no-whitespace JSON -> SHA256, prefixed 'sha256:'. This mirrors Polymer's
SemanticRunID.param_signature canonicalization (the intended basis for Python/R hash parity),
and is reused by both `analysis_profile.content_hash` (the profile address) and
`contracts.load_contract` (the dimnames_hash). One recipe, one place.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_sha256(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
