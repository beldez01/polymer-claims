# Adapter Trust Registry — Design Spec

**Date:** 2026-06-05
**Status:** Approved (2 forks resolved by user: hold-PENDING + protocol-side audit).
**Source:** external audit finding #5 (`/Users/zbb2/Desktop/polymer-claims-audit.md`) — *"the adapter air gap is identity-string based; no registry proves verifier independence."*

## Problem

The grammar's `verify()` air gap mints a `Satisfaction` only when ≥2 **distinct adapter identity strings** agree (`grammar/evaluate.py`). Its own docstring concedes: identity-string uniqueness is *necessary but not sufficient* — a single actor can supply two cosmetically-different adapters and forge a "two implementations agreed" license. Today `"two implementations agreed"` means only `"two identity strings differed."` We make it mean genuine independence: **different owner, different implementation lineage, both trusted** — enforced by an operator-curated registry, not adapter self-description.

## Shape (mirrors the existing `OracleRegistry` precedent exactly)

The `OracleRegistry` is the template: a frozen registry **passed into `run_cycle`, never persisted in the Corpus** (Corpus stays 4 collections), consulted at the LICENSED-mint seam in `verify_stage` (where `oracle_cap` already sits). The adapter trust registry is its twin.

### Grammar — ONE additive change
- `PendingReason.ADAPTER_NOT_INDEPENDENT = "adapter_not_independent"` (the 11th reason; additive, precedented by #5a's `MATERIALIZATION_DRIFTED`). Nothing else in grammar changes — the frozen `Satisfaction`/`Licensing`/`Claim` models are untouched (the "protocol-side audit" fork was chosen precisely to avoid a Satisfaction field).

### Protocol — new module `adapter_registry.py` (sibling to `oracle.py`)
- `AdapterCredential(_Model)`: `identity: str`, `owner: str`, `implementation_hash: str`, `version: str = "v1"`, `trusted: bool = True`. (The operator asserts these — the adapter does NOT self-describe them, which is the whole security point: an adapter can't lie about its owner because the registry, not the adapter, is the authority.)
- `AdapterRegistry(_Model)`: `credentials: tuple[AdapterCredential, ...] = ()`; `resolve(identity) -> AdapterCredential | None`; `is_empty` property. Frozen, passed-in, never persisted.
- `adapters_independent(a: AdapterCredential, b: AdapterCredential) -> bool` (pure): `a.trusted and b.trusted and a.owner != b.owner and a.implementation_hash != b.implementation_hash`. (The audit's exact refusal triad: same owner OR same implementation lineage OR untrusted ⇒ NOT independent.)
- `pair_is_registry_independent(registry, identities: tuple[str, ...]) -> bool` (pure): True iff SOME pair among the producing identities resolves (both) to credentials that are `adapters_independent`. With a registry supplied, an **unregistered** identity resolves to `None` ⇒ contributes no independent pair (treated as untrusted).

### Protocol — the gate in `verify_stage`
- New kwarg `adapter_registry: AdapterRegistry | None = None` (threaded from `run_cycle`).
- Inside the existing LICENSED block (`if ev.satisfaction is not None and c.id in in_ext and provenance and c.id in permitted:`), as the FIRST check — BEFORE the representation-revision / ordinary split (independence is a precondition for ANY license route):
  ```
  if adapter_registry is not None and not adapter_registry.is_empty:
      identities = tuple(r.adapter_identity for r in ev.results)
      if not pair_is_registry_independent(adapter_registry, identities):
          new_claims.append(_with_status(c, status=Status.PENDING,
                                          pending_reason=PendingReason.ADAPTER_NOT_INDEPENDENT,
                                          licensing=None))
          continue
  ```
  (The claim is already PENDING in-flight; `_with_status` re-stamps it with the specific reason and re-validates via `Claim.model_validate`, exactly like the other status transitions in this file.)
- **Back-compat (opt-in tightening):** `adapter_registry is None` OR `is_empty` ⇒ the gate is skipped ⇒ today's behavior (grammar's identity-distinctness is the only air-gap) is byte-unchanged. Every existing test stays green. Supplying a non-empty registry = "enforce trust."

### Protocol — wiring + audit (`cycle.py`)
- `run_cycle(..., adapter_registry: AdapterRegistry | None = None)` threads it into `verify_stage`.
- **Protocol-side audit (the chosen fork):** two channels, NO new structures —
  1. **Persisted, per-claim:** a held claim carries `pending_reason=ADAPTER_NOT_INDEPENDENT` — permanently visible on the claim (why it didn't license).
  2. **Ephemeral, per-cycle:** `cycle.py` post-counts the held set from the returned corpus and enriches the existing `verify_stage` `StageAudit.note` → e.g. `"{n_licensed} licensed, {n_trust_held} held (adapter not independent)"`. (The agreeing adapter IDENTITIES are already retained in the cycle's `ExecRecord.evaluation.results[*].adapter_identity`, so per-claim attribution is already auditable; this slice adds the independence verdict.)

### Public exports (`polymer_protocol/__init__.py`)
`AdapterCredential`, `AdapterRegistry`, `adapters_independent`, `pair_is_registry_independent`.

## Determinism / purity / invariants
- The registry + predicates are pure/deterministic (frozen models, no clock/random/IO). The registry is passed in, NEVER persisted — Corpus stays 4 collections. Grammar gains exactly one enum value; the frozen `Satisfaction`/`Licensing` models are untouched. The one-way grammar↔protocol isolation holds.

## Acceptance
- `adapters_independent` truth table: distinct-owner + distinct-hash + both-trusted ⇒ True; same owner ⇒ False; same implementation_hash ⇒ False; either untrusted ⇒ False.
- Through `run_cycle`: **no/empty registry ⇒ a claim that licensed before STILL licenses** (back-compat, byte-identical). With a registry where the two reference adapters are registered as independent ⇒ licenses. With a registry where they share owner / share implementation_hash / one untrusted / one unregistered ⇒ the claim is **held PENDING with `ADAPTER_NOT_INDEPENDENT`, NOT licensed**.
- The `verify_stage` StageAudit note reflects the held count. Determinism (byte-identical CycleResult across runs) + belief-neutrality (the gate only WITHHOLDS a license; it never changes the grounded extension or beliefs of other claims) hold through `run_cycle`. Grammar + protocol suites green; ruff clean; isolation both ways.

## Non-goals (this slice)
- A `Satisfaction`/`Licensing` grammar field recording credential ids (the heavier provenance fork — deferred; the persisted `pending_reason` + ephemeral note + retained ExecRecord identities suffice for now).
- Cryptographic attestation / real implementation-hashing of adapter code (the `implementation_hash` is an operator-asserted string; computing it from real adapter bytes is future work).
- A "require registration for ALL license-grade" strict mode (today: registry supplied ⇒ enforce; absent ⇒ legacy identity-distinctness). A strict-mode knob is a noted follow-up.
- Capability tags / fine-grained independence policies beyond owner+lineage+trust.
- Verifier-authority decay (that is the oracle-validation daemon's job, #5b).
