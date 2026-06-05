"""ORACLE-VALIDATION daemon (#5b) — decay a failing oracle's ValidationTier from known-answer SPOT
probes, tightening the #2 oracle_cap seam on the next cycle.

Pure / deterministic / caller-scheduled (the standing #5 invariant): no clock, no randomness, no
environment read — probe OUTCOMES are arguments (the caller ran the oracle on a known input OUTSIDE the
pure core, like adapters live outside the package). Returns a threaded registry-delta + a record; the
registry is execution-environment state, never in the Corpus. Decay-only: never auto-promotes.
"""
from __future__ import annotations

from polymer_grammar import ValidationTier, decay_tier

from .base import _Model
from .oracle import OracleRegistry


class SpotProbe(_Model):
    """One known-answer probe outcome for an oracle. `label` is optional, for the record/audit."""

    oracle_id: str
    passed: bool
    label: str | None = None


class OracleDecay(_Model):
    oracle_id: str
    probes_run: int
    probes_passed: int
    tier_before: ValidationTier
    tier_after: ValidationTier


class OracleValidationRecord(_Model):
    decays: tuple[OracleDecay, ...] = ()        # one per REGISTRY oracle that had >=1 probe
    unknown_oracle_ids: tuple[str, ...] = ()    # probe oracle_ids absent from the registry (inert)


def oracle_validation_pass(
    registry: OracleRegistry, *, probes: tuple[SpotProbe, ...]
) -> tuple[OracleRegistry, OracleValidationRecord]:
    """Run the SPOT probes against the registry's oracles; decay each probed oracle's tier proportional to
    its pass rate. Returns a NEW registry with decayed dossiers (the input is never mutated) + a record.
    Oracles with no probes pass through unchanged; probes for unknown oracle ids are recorded but inert."""
    run: dict[str, int] = {}
    passed: dict[str, int] = {}
    for p in probes:
        run[p.oracle_id] = run.get(p.oracle_id, 0) + 1
        passed[p.oracle_id] = passed.get(p.oracle_id, 0) + (1 if p.passed else 0)

    known = {d.oracle_id for d in registry.dossiers}
    unknown = tuple(sorted(oid for oid in run if oid not in known))

    decays: list[OracleDecay] = []
    new_dossiers = []
    changed = False
    for d in registry.dossiers:
        if d.oracle_id not in run:
            new_dossiers.append(d)
            continue
        n = run[d.oracle_id]
        ok = passed[d.oracle_id]
        new_tier = decay_tier(d.validation_tier, ok / n)
        decays.append(
            OracleDecay(
                oracle_id=d.oracle_id, probes_run=n, probes_passed=ok,
                tier_before=d.validation_tier, tier_after=new_tier,
            )
        )
        if new_tier != d.validation_tier:
            new_dossiers.append(d.model_copy(update={"validation_tier": new_tier}))
            changed = True
        else:
            new_dossiers.append(d)

    record = OracleValidationRecord(
        decays=tuple(sorted(decays, key=lambda x: x.oracle_id)),
        unknown_oracle_ids=unknown,
    )
    if not changed:
        return registry, record
    return OracleRegistry(dossiers=tuple(new_dossiers)), record
