"""Append-only JSONL event log + epoch allocator for the calibration ledger (impure: filesystem).
NOT re-exported from polymer_claims.__init__.

Architecture:
  - append_records / load_ledger: durable JSONL log; latest line wins per (claim_id, epoch).
  - EpochAllocator: persists per-claim {epoch, identity} JSON so allocate() is idempotent
    across ticks AND process restarts.
  - observe_anchored: builds a PressureContext from snapshot diffs and calls anchored_resolutions.
"""
from __future__ import annotations

import json
from pathlib import Path

from polymer_grammar import Status
from polymer_protocol.calibration import (
    CalibrationLedger,
    GeneratingModelParams,
    PressureContext,
    PressureKind,
    ResolutionRecord,
    anchored_resolutions,
)


# ── JSONL event log ────────────────────────────────────────────────────────────


def append_records(path, records) -> None:
    """Append ResolutionRecord objects to a JSONL file (append-only; atomic per-line)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        for r in records:
            fh.write(r.model_dump_json(exclude_none=True) + "\n")


def load_ledger(
    path, *, generating_models: tuple[GeneratingModelParams, ...] = ()
) -> CalibrationLedger:
    """Read the JSONL and fold events to the latest verdict per (subject_claim_id, license_epoch).

    Latest line wins (definitional append-only semantics). First-seen order is preserved so the
    ledger has a stable deterministic ordering even as new records accumulate."""
    path = Path(path)
    latest: dict[tuple[str, int], ResolutionRecord] = {}
    order: list[tuple[str, int]] = []
    if path.is_file():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = ResolutionRecord.model_validate_json(line)
            key = (r.subject_claim_id, r.license_epoch)
            if key not in latest:
                order.append(key)
            latest[key] = r  # latest event wins
    return CalibrationLedger(
        records=tuple(latest[k] for k in order),
        generating_models=generating_models,
    )


# ── EpochAllocator ─────────────────────────────────────────────────────────────


class EpochAllocator:
    """Owns license_epoch assignment (spec §6).

    Persists per-claim last epoch + identity key as JSON so allocate() is idempotent
    across ticks AND process restarts:
      - new identity-key (first time or semantic_run_id changed) → epoch bumped by 1.
      - same identity-key → same epoch (no change, no write needed but we still flush
        for correctness in multi-step pipelines).

    Identity key:
      claim.licensing.satisfactions[0].materialization.semantic_run_id when present,
      else a fallback string "{claim.id}|{n_satisfactions}" (stable for non-content-addressed
      licenses that never change run identity).
    """

    def __init__(self, path) -> None:
        self.path = Path(path)
        self._state: dict[str, dict] = {}
        if self.path.is_file():
            self._state = json.loads(self.path.read_text())

    def _identity(self, claim) -> str:
        lic = claim.licensing
        if lic and lic.satisfactions:
            srid = lic.satisfactions[0].materialization.semantic_run_id
            if srid:
                return srid
        # Fallback: stable string for claims without a semantic_run_id
        n_sats = len(lic.satisfactions) if lic else 0
        return f"{claim.id}|{n_sats}"

    def allocate(self, corpus) -> dict[str, int]:
        """Return {claim_id: epoch} for currently-LICENSED claims; bump on new identity key."""
        out: dict[str, int] = {}
        for c in corpus.claims:
            if c.status != Status.LICENSED:
                continue
            ident = self._identity(c)
            prev = self._state.get(c.id)
            if prev is None:
                epoch = 0
            elif prev["identity"] == ident:
                epoch = prev["epoch"]        # same identity -> same epoch (idempotent)
            else:
                epoch = prev["epoch"] + 1   # re-licensed under a changed identity
            self._state[c.id] = {"epoch": epoch, "identity": ident}
            out[c.id] = epoch
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._state, sort_keys=True))
        return out


# ── ANCHORED tap ───────────────────────────────────────────────────────────────


def observe_anchored(
    prev,
    curr,
    cycle: int,
    *,
    allocator: EpochAllocator,
    last_drift=None,
) -> tuple[ResolutionRecord, ...]:
    """Build a PressureContext from prev→curr corpus snapshot diff and emit ANCHORED records.

    Cause classification:
      LICENSED → REJECTED               → PressureKind.DEFEAT
      LICENSED → PENDING (in last_drift.drifted) → PressureKind.DRIFT

    Epochs are captured from the PRE-transition (prev) licensed set so the epoch is always
    the epoch the claim held when it was under pressure — not a potentially-bumped post-tick value.
    """
    epoch_map = allocator.allocate(prev)  # epochs as of the PRE-transition LICENSED set
    cause: dict[str, PressureKind] = {}

    prev_licensed = {c.id for c in prev.claims if c.status == Status.LICENSED}
    by_id = {c.id: c for c in curr.claims}
    drift_ids = {f.claim_id for f in (last_drift.drifted if last_drift is not None else ())}

    for cid in prev_licensed:
        c = by_id.get(cid)
        if c is None:
            continue
        if c.status == Status.REJECTED:
            cause[cid] = PressureKind.DEFEAT
        elif c.status == Status.PENDING and cid in drift_ids:
            cause[cid] = PressureKind.DRIFT

    pc = PressureContext(epoch=epoch_map, cause=cause)
    return anchored_resolutions(prev, curr, cycle, pc)
