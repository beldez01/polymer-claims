from polymer_protocol import (
    AdapterCredential,
    AdapterRegistry,
    adapters_independent,
    independent_credential_pair,
    pair_is_registry_independent,
)


def _cred(identity, owner, h, trusted=True):
    return AdapterCredential(identity=identity, owner=owner, implementation_hash=h, trusted=trusted)


def test_independent_truth_table():
    a = _cred("x", "alice", "h1")
    b = _cred("y", "bob", "h2")
    assert adapters_independent(a, b)
    assert not adapters_independent(a, _cred("z", "alice", "h2"))            # same owner
    assert not adapters_independent(a, _cred("z", "bob", "h1"))             # same lineage
    assert not adapters_independent(a, _cred("z", "bob", "h2", trusted=False))  # untrusted


def test_resolve_and_is_empty():
    r = AdapterRegistry()
    assert r.is_empty and r.resolve("x") is None
    r2 = AdapterRegistry(credentials=(_cred("x", "alice", "h1"),))
    assert not r2.is_empty
    assert r2.resolve("x").owner == "alice"
    assert r2.resolve("nope") is None


def test_pair_is_registry_independent():
    r = AdapterRegistry(credentials=(_cred("identity", "alice", "h1"), _cred("reference", "bob", "h2")))
    assert pair_is_registry_independent(r, ("identity", "reference"))
    assert not pair_is_registry_independent(r, ("identity", "ghost"))       # unregistered -> no pair
    r2 = AdapterRegistry(credentials=(_cred("identity", "alice", "h1"), _cred("reference", "alice", "h2")))
    assert not pair_is_registry_independent(r2, ("identity", "reference"))   # same owner


def test_independent_credential_pair_returns_witness_pair():
    r = AdapterRegistry(credentials=(_cred("identity", "alice", "h1"), _cred("reference", "bob", "h2")))
    assert independent_credential_pair(r, ("identity", "reference")) == ("identity", "reference")
    assert independent_credential_pair(r, ("identity", "ghost")) is None


def test_frozen_and_json_roundtrips():
    r = AdapterRegistry(credentials=(_cred("x", "alice", "h1"),))
    assert AdapterRegistry.model_validate_json(r.model_dump_json()) == r
