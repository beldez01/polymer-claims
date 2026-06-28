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
    ResolutionKind,
    ResolutionRecord,
    anchored_resolutions,
)


# ── JSONL event log ────────────────────────────────────────────────────────────


def _fold_key(r: ResolutionRecord):
    # ATTESTED is an event-level tier: distinct external determinations on the same claim/epoch
    # must coexist, keyed by a per-event discriminator. This ingester always sets source_claim_id,
    # but the pure model keeps it optional (set iff the event is a corpus claim), so fall back to
    # attestation_ref for source-less records. DEFINITIONAL/ANCHORED keep the original
    # (subject_claim_id, license_epoch) identity (latest verdict wins).
    if r.resolution_kind == ResolutionKind.ATTESTED:
        discriminator = r.source_claim_id or r.attestation_ref
        return (r.subject_claim_id, r.license_epoch, "attested", discriminator)
    return (r.subject_claim_id, r.license_epoch)


def _sidecar_path(path) -> Path:
    """The generating-models sidecar that lives alongside a JSONL ledger."""
    return Path(str(path) + ".models.json")


def append_records(path, records) -> None:
    """Append ResolutionRecord objects to a JSONL file (append-only; one JSON object per line).

    Note: raw JSONL line count is NOT the record count. Re-ingesting the same determination
    appends a duplicate line; ``load_ledger`` folds to one record per fold key at read time."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        for r in records:
            fh.write(r.model_dump_json(exclude_none=True) + "\n")


def dump_models(path, models) -> None:
    """Write generating models to a sidecar file alongside the JSONL ledger.

    Writes a JSON array of GeneratingModelParams dicts to `<path>.models.json`.
    If models is empty, the sidecar is not written (nothing to persist)."""
    if not models:
        return
    sidecar = _sidecar_path(path)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(
        json.dumps([m.model_dump(mode="json") for m in models])
    )


def load_ledger(
    path, *, generating_models: tuple[GeneratingModelParams, ...] = ()
) -> CalibrationLedger:
    """Read the JSONL and fold events to the latest verdict per fold key.

    Fold identity by tier:
      - ATTESTED: ``(subject_claim_id, license_epoch, "attested", discriminator)`` where
        ``discriminator = source_claim_id or attestation_ref``.  Each distinct external
        determination on the same claim/epoch gets its own slot, so multiple sources coexist.
        If both are None the discriminator is None and such records collapse to one (accepted
        behavior — source-less attestations carry no event identity).
      - DEFINITIONAL / ANCHORED: ``(subject_claim_id, license_epoch)`` — latest verdict wins.

    Latest line wins (definitional append-only semantics). First-seen order is preserved so the
    ledger has a stable deterministic ordering even as new records accumulate.

    If `generating_models` is not explicitly supplied and a sidecar `<path>.models.json` exists,
    models are auto-loaded from it so `certify` can show n_generated without extra caller plumbing."""
    path = Path(path)
    latest: dict[tuple, ResolutionRecord] = {}
    order: list[tuple] = []
    if path.is_file():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = ResolutionRecord.model_validate_json(line)
            key = _fold_key(r)
            if key not in latest:
                order.append(key)
            latest[key] = r  # latest event wins
    # Auto-load generating_models from sidecar when caller did not supply explicit ones
    if not generating_models:
        sidecar = _sidecar_path(path)
        if sidecar.is_file():
            raw = json.loads(sidecar.read_text())
            generating_models = tuple(GeneratingModelParams(**d) for d in raw)
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

    def allocate(self, corpus, cycle: int | None = None) -> dict[str, int]:
        """Return {claim_id: epoch} for currently-LICENSED claims; bump on new identity key.

        `cycle` (when supplied) records the exposure clock — the cycle an epoch was first observed
        LICENSED — so the hazard rate can measure survival time. A same-identity epoch keeps its
        original start; a new/bumped epoch starts a fresh clock at `cycle`."""
        out: dict[str, int] = {}
        for c in corpus.claims:
            if c.status != Status.LICENSED:
                continue
            ident = self._identity(c)
            prev = self._state.get(c.id)
            if prev is None:
                epoch, start = 0, cycle
            elif prev["identity"] == ident:
                epoch = prev["epoch"]                       # same identity -> same epoch (idempotent)
                start = prev.get("start_cycle", cycle)      # keep the original exposure clock
            else:
                epoch, start = prev["epoch"] + 1, cycle     # re-licensed -> a fresh exposure clock
            self._state[c.id] = {"epoch": epoch, "identity": ident, "start_cycle": start}
            out[c.id] = epoch
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._state, sort_keys=True))
        return out

    def start_cycle_of(self, claim_id: str) -> int | None:
        """The cycle the claim's current epoch was first observed LICENSED (its exposure start)."""
        s = self._state.get(claim_id)
        return s.get("start_cycle") if s else None


# ── ANCHORED tap ───────────────────────────────────────────────────────────────


def observe_anchored(
    prev,
    curr,
    cycle: int,
    *,
    allocator: EpochAllocator,
    last_drift=None,
    drift_ran: bool = False,
) -> tuple[ResolutionRecord, ...]:
    """Build a PressureContext from prev→curr corpus snapshot diff and emit ANCHORED records.

    Cause classification (a claim LICENSED in `prev`):
      → REJECTED                                  → DEFEAT  (failed)
      → PENDING and in `last_drift.drifted`        → DRIFT   (failed)
      → still LICENSED, `drift_ran`, not drifted   → DRIFT   (UPHELD — survived a drift re-check)

    `drift_ran` says a DRIFT pass executed this tick (the caller knows the tick's action). A drift
    pass scans the whole LICENSED set, so a claim LICENSED in `prev` that is still LICENSED in `curr`
    and absent from `last_drift.drifted` was *examined and survived* → an UPHELD warrant-survival
    event. Mere persistence on a non-drift tick is NOT a survival event (so `q_anchored` cannot
    drift with tick frequency). The per-(claim, epoch) fold collapses repeated survivals to one.

    Epochs are captured from the PRE-transition (prev) licensed set so the epoch is always
    the epoch the claim held when it was under pressure — not a potentially-bumped post-tick value.
    """
    epoch_map = allocator.allocate(prev, cycle)  # epochs + exposure clocks for the PRE-transition set
    cause: dict[str, PressureKind] = {}
    survived: set[str] = set()

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
        elif drift_ran and c.status == Status.LICENSED and cid not in drift_ids:
            cause[cid] = PressureKind.DRIFT  # a drift re-check fired and the license was RETAINED
            survived.add(cid)

    exposure_start = {
        cid: s for cid in cause if (s := allocator.start_cycle_of(cid)) is not None
    }
    pc = PressureContext(
        epoch=epoch_map, cause=cause, survived=frozenset(survived), exposure_start=exposure_start
    )
    return anchored_resolutions(prev, curr, cycle, pc)
