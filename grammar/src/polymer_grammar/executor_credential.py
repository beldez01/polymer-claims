"""executor_credential.py — ExecutorDescriptor, ExecutorDescriptorRegistry,
ExecutorTrustEntry, ExecutorTrustRegistry (V2.0 evidence-licensed capability).

Pure / numpy-free: grammar + stdlib only."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import model_validator

from .base import _Model
from .operations import _sha

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

_CANONICAL_ROLE_ORDER: tuple[str, ...] = (
    "predictor",
    "baseline_predictor",
    "scorer",
    "evidence_transform",
)


def _is_sha256_ref(value: str) -> bool:
    return bool(_SHA256_RE.match(value))


class Component(_Model):
    """A single executable unit within an executor, identified by role."""

    role: Literal["predictor", "baseline_predictor", "scorer", "evidence_transform"]
    identity: str
    implementation_hash: str
    config_hash: str

    @model_validator(mode="after")
    def _validate(self) -> Component:
        if not self.identity.strip():
            raise ValueError("identity must be non-empty")
        if not _is_sha256_ref(self.implementation_hash):
            raise ValueError(
                f"implementation_hash must be 'sha256:<64 lowercase hex>', "
                f"got {self.implementation_hash!r}"
            )
        if not _is_sha256_ref(self.config_hash):
            raise ValueError(
                f"config_hash must be 'sha256:<64 lowercase hex>', "
                f"got {self.config_hash!r}"
            )
        return self


class ExecutorDescriptor(_Model):
    """Versioned descriptor of an executor: exactly one component per role,
    in canonical role order, with unique identities."""

    components: tuple[Component, ...]
    version: str

    @model_validator(mode="after")
    def _validate(self) -> ExecutorDescriptor:
        roles = [c.role for c in self.components]

        # Exactly one of each role (checks for missing and duplicates together)
        role_counts: dict[str, int] = {}
        for r in roles:
            role_counts[r] = role_counts.get(r, 0) + 1

        missing = [r for r in _CANONICAL_ROLE_ORDER if role_counts.get(r, 0) == 0]
        if missing:
            raise ValueError(
                f"ExecutorDescriptor missing required roles: {missing}"
            )

        duplicated = [r for r, count in role_counts.items() if count > 1]
        if duplicated:
            raise ValueError(
                f"ExecutorDescriptor has duplicate roles: {duplicated}"
            )

        # Canonical role order
        if roles != list(_CANONICAL_ROLE_ORDER):
            raise ValueError(
                f"components must be in canonical role order "
                f"{list(_CANONICAL_ROLE_ORDER)}, got {roles}"
            )

        # Unique identities
        identities = [c.identity for c in self.components]
        if len(identities) != len(set(identities)):
            seen: set[str] = set()
            dupes = sorted({i for i in identities if i in seen or seen.add(i)})  # type: ignore[func-returns-value]
            raise ValueError(
                f"Component identities must be unique; duplicates: {dupes}"
            )

        return self

    @property
    def content_hash(self) -> str:
        canonical = {
            "version": self.version,
            "components": [
                {
                    "role": c.role,
                    "identity": c.identity,
                    "implementation_hash": c.implementation_hash,
                    "config_hash": c.config_hash,
                }
                for c in self.components
            ],
        }
        return "sha256:" + _sha(canonical)


class ExecutorDescriptorRegistry(_Model):
    """Registry of ExecutorDescriptor objects; enforces unique content_hash."""

    descriptors: tuple[ExecutorDescriptor, ...] = ()

    @model_validator(mode="after")
    def _unique_hashes(self) -> ExecutorDescriptorRegistry:
        seen: set[str] = set()
        for d in self.descriptors:
            ch = d.content_hash
            if ch in seen:
                raise ValueError(
                    f"duplicate content_hash in ExecutorDescriptorRegistry: {ch}"
                )
            seen.add(ch)
        return self

    def resolve(self, content_hash: str) -> ExecutorDescriptor | None:
        for d in self.descriptors:
            if d.content_hash == content_hash:
                return d
        return None


class ExecutorTrustEntry(_Model):
    """Trust decision for a specific executor descriptor."""

    descriptor_ref: str
    owner: str
    trusted: bool
    version: str

    @model_validator(mode="after")
    def _validate(self) -> ExecutorTrustEntry:
        if not _is_sha256_ref(self.descriptor_ref):
            raise ValueError(
                f"descriptor_ref must be 'sha256:<64 lowercase hex>', "
                f"got {self.descriptor_ref!r}"
            )
        if not self.owner.strip():
            raise ValueError("owner must be non-empty")
        return self


class ExecutorTrustRegistry(_Model):
    """Registry of ExecutorTrustEntry objects; enforces unique descriptor_ref."""

    entries: tuple[ExecutorTrustEntry, ...] = ()

    @model_validator(mode="after")
    def _unique_refs(self) -> ExecutorTrustRegistry:
        seen: set[str] = set()
        for e in self.entries:
            if e.descriptor_ref in seen:
                raise ValueError(
                    f"duplicate descriptor_ref in ExecutorTrustRegistry: "
                    f"{e.descriptor_ref}"
                )
            seen.add(e.descriptor_ref)
        return self

    def resolve(self, descriptor_ref: str) -> ExecutorTrustEntry | None:
        for e in self.entries:
            if e.descriptor_ref == descriptor_ref:
                return e
        return None
