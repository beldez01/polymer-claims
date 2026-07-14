"""adapter_registry.py — adapter trust registry.

Passed into run_cycle like OracleRegistry, NEVER persisted in the Corpus. Proves verifier
INDEPENDENCE (different owner / implementation lineage / both trusted), the stronger guarantee
the grammar air-gap's identity-string distinctness cannot give.
"""
from __future__ import annotations

from .base import _Model


class AdapterCredential(_Model):
    """Operator-ASSERTED trust metadata for one adapter identity. The adapter does NOT
    self-describe these (an adapter can't be trusted to declare its own owner) — the
    registry, curated by the corpus operator, is the authority."""

    identity: str
    owner: str
    implementation_hash: str
    version: str = "v1"
    trusted: bool = True
    # R1 (adapter-independence hardening): provenance-lineage tags — the shared roots that make two
    # differently-owned adapters fail on the SAME inputs (org, model family, training corpus, shared
    # reference DB, e.g. "org:deepmind" / "trained_on:clinvar"). Two adapters sharing ANY lineage tag
    # are NOT independent even with distinct owner + implementation_hash. Empty (default) => no
    # constraint, so existing registries are unaffected. Never persisted in the Corpus.
    lineage: tuple[str, ...] = ()


class AdapterRegistry(_Model):
    """Frozen registry of AdapterCredentials. Passed into run_cycle; never stored in the Corpus."""

    credentials: tuple[AdapterCredential, ...] = ()

    def resolve(self, identity: str) -> AdapterCredential | None:
        for c in self.credentials:
            if c.identity == identity:
                return c
        return None

    @property
    def is_empty(self) -> bool:
        return not self.credentials


def adapters_independent(a: AdapterCredential, b: AdapterCredential) -> bool:
    """Two adapters are INDEPENDENT iff both trusted AND different owner AND different
    implementation lineage AND no SHARED provenance-lineage tag. (The refusal quad: same owner OR
    same implementation lineage OR a shared lineage tag OR untrusted => NOT independent.) A shared
    lineage tag (same org / training corpus / reference DB) makes two differently-owned adapters fail
    together, defeating the air-gap even when owner and implementation_hash differ. Empty lineage on
    either side shares nothing, so registries without lineage behave exactly as before."""
    return (
        a.trusted and b.trusted
        and a.owner != b.owner
        and a.implementation_hash != b.implementation_hash
        and set(a.lineage).isdisjoint(b.lineage)
    )


def pair_is_registry_independent(registry: AdapterRegistry, identities: tuple[str, ...]) -> bool:
    """True iff SOME pair among the producing `identities` resolves (both) to registered
    credentials that are `adapters_independent`. An UNREGISTERED identity resolves to None and
    so contributes no independent pair (treated as untrusted under an active registry)."""
    return independent_credential_pair(registry, identities) is not None


def independent_credential_pair(
    registry: AdapterRegistry, identities: tuple[str, ...]
) -> tuple[str, str] | None:
    """Return the first producing credential-identity pair that proves registry independence.

    This is the audit witness stored on a minted Satisfaction. None means no independent pair
    exists under the active registry.
    """
    creds = [registry.resolve(i) for i in identities]
    n = len(creds)
    for i in range(n):
        for j in range(i + 1, n):
            ca, cb = creds[i], creds[j]
            if ca is not None and cb is not None and adapters_independent(ca, cb):
                return (ca.identity, cb.identity)
    return None
