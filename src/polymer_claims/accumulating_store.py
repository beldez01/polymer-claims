"""Accumulating-universe store (B2) — one atom, many links.

Persist the WHOLE Corpus (all 4 collections incl the live ``fdr_ledger``) as an authoritative
snapshot, plus an append-only, content-addressed claim log (the audit trail + dedup index + census
substrate). The load -> propose -> dedup -> register -> license -> persist-back cycle makes a re-run
mint zero claims and turns the ``fdr_ledger`` into an accumulating stream (the substrate online
e-LOND was built for) instead of a fresh per-run scratch object.

Spec: docs/superpowers/specs/2026-07-10-accumulating-universe-store-design.md.
Umbrella-side only; ``Corpus`` stays 4; grammar/protocol untouched. Reuses ``io`` for the snapshot
round-trip. DuckDB is not a dependency, so the census is pure-python over the log/corpus.

v1 scope = the store PRIMITIVE, exercised on synthetic corpora. Wiring the real ``populate_universe``
(the ~13-min GDSC scan) and the viewer at this store is a separate follow-up (see spec §6 / BACKLOG).
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from polymer_grammar import Claim, DataHandle, FDRLedger
from polymer_protocol import Corpus

from polymer_claims import measurement_space as ms
from polymer_claims.io import dump_corpus, load_corpus

# The register+license step is INJECTED so the store stays generic: it changes only what corpus is
# loaded and proposed against, never how standing is earned (Spec 1 §2.4). Real callers pass the
# pharmaco/spine preregister+license_batch pipeline; tests pass a synthetic register fn.
RegisterLicenseFn = Callable[[Corpus, "tuple[Claim, ...]"], Corpus]

_MODALITY_NONE = "∅"  # ∅ — a claim reading no registered contract (modality not derivable)


def content_address(claim: Claim) -> str:
    """SHA-256 over a claim's canonical JSON dump — the same recipe ``merge_universes`` uses, so a
    byte-identical re-observed atom always hashes equal. Stable across runs for a freshly-proposed
    claim (status/evidence are part of the hash, so this is the *fresh proposal's* identity)."""
    return "sha256:" + hashlib.sha256(claim.model_dump_json().encode("utf-8")).hexdigest()


def _data_refs(claim: Claim) -> tuple[str, ...]:
    """Every SE-Contract ref the claim's evaluation plan reads (its ``DataHandle`` inputs)."""
    plan = claim.evaluation_plan
    if plan is None:
        return ()
    refs = {inp.ref for node in plan.graph.nodes for inp in node.inputs if isinstance(inp, DataHandle)}
    return tuple(sorted(refs))


def _strip_scheme(ref: str) -> str:
    return ref[len("se:"):] if ref.startswith("se:") else ref


def contract_uids(claim: Claim) -> tuple[str, ...]:
    """The contract uids (no ``se:`` prefix) the claim reads — the realized measurement spaces."""
    return tuple(sorted({_strip_scheme(r) for r in _data_refs(claim)}))


def claim_modalities(claim: Claim) -> tuple[ms.Modality, ...]:
    """The registry modalities of every measurement space the claim's contracts expose
    (deterministic, sorted by value). Empty if the claim reads no registered contract. A
    multi-space contract (e.g. pharmaco = methylation + drug-response) contributes both, honestly,
    rather than guessing which the plan's row-prefix reads."""
    mods = {sp.modality for uid in contract_uids(claim) for sp in ms.spaces_for_contract(uid)}
    return tuple(sorted(mods, key=lambda m: m.value))


def _subject_key(claim: Claim) -> str:
    """A deterministic subject facet key. The exact subject JSON (byte-identical subjects group);
    subject-CLASS coarsening is a deferred refinement (spec §5)."""
    return claim.subject.model_dump_json() if claim.subject is not None else _MODALITY_NONE


class ClaimLogRecord(BaseModel):
    """One append-only line in ``claims.jsonl`` — the registration event + its query facets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content_address: str
    claim_id: str
    subject_key: str
    pattern: str
    registered_status: str          # status at registration (audit); current status is in the snapshot
    contract_uids: tuple[str, ...] = ()
    modalities: tuple[str, ...] = ()
    generated_by: str | None = None
    agent_id: str | None = None

    @classmethod
    def of(cls, claim: Claim) -> "ClaimLogRecord":
        prov = claim.provenance
        return cls(
            content_address=content_address(claim),
            claim_id=claim.id,
            subject_key=_subject_key(claim),
            pattern=f"{claim.pattern.id}@{claim.pattern.version}",
            registered_status=claim.status.value,
            contract_uids=contract_uids(claim),
            modalities=tuple(m.value for m in claim_modalities(claim)),
            generated_by=prov.generated_by.value if prov is not None else None,
            agent_id=prov.agent_id if prov is not None else None,
        )


@dataclass(frozen=True)
class AccumulateResult:
    n_proposed: int
    n_new: int
    n_deduped: int
    corpus: Corpus


@dataclass(frozen=True)
class Census:
    """A coverage census over (subject × modality × status) — a plain report, no meta-claims."""

    cells: Mapping[tuple[str, str], Mapping[str, int]]
    subjects: tuple[str, ...]
    modalities: tuple[str, ...]
    coverage_gaps: tuple[tuple[str, str], ...]  # (subject, modality) cells empty among observed axes


class AccumulatingStore:
    """One append-only store rooted at a directory:

    * ``corpus.json`` — the authoritative whole-``Corpus`` snapshot (all 4 collections incl the live
      ``fdr_ledger``); the current, revisable state. Reuses ``io.load_corpus``/``dump_corpus``.
    * ``claims.jsonl`` — the append-only, content-addressed audit log; the dedup index + census
      substrate. Monotone: never loses a line, even when a claim is later demoted in the snapshot.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.corpus_path = self.root / "corpus.json"
        self.log_path = self.root / "claims.jsonl"

    def load_corpus(self, *, target_fdr: float = 0.05) -> Corpus:
        if self.corpus_path.exists():
            return load_corpus(self.corpus_path)
        return Corpus(fdr_ledger=FDRLedger(target_fdr=target_fdr))

    def log_records(self) -> tuple[ClaimLogRecord, ...]:
        if not self.log_path.exists():
            return ()
        return tuple(
            ClaimLogRecord.model_validate_json(line)
            for line in self.log_path.read_text().splitlines()
            if line.strip()
        )

    def registered_ids(self) -> frozenset[str]:
        """The dedup index: ids of every claim ever registered (deterministic per subject/params)."""
        return frozenset(r.claim_id for r in self.log_records())

    def accumulate(self, proposed: Iterable[Claim], register_license: RegisterLicenseFn) -> AccumulateResult:
        """Load -> dedup (by claim id) -> register+license only the genuinely-new -> persist back.

        Re-proposing the same panel mints zero: already-registered ids are dropped before the gate,
        so the ``fdr_ledger`` is not re-charged and the corpus does not grow.
        """
        proposed = tuple(proposed)
        corpus = self.load_corpus()
        # Dedup against BOTH the log and the corpus's existing ids (belt-and-suspenders: if the
        # snapshot and log ever desync, a claim already in the corpus is still not re-registered —
        # which would violate the Corpus unique-id invariant on reload), and within this batch.
        seen = set(self.registered_ids()) | set(corpus.by_id())
        new: list[Claim] = []
        for c in proposed:
            if c.id in seen:
                continue
            seen.add(c.id)
            new.append(c)
        new = tuple(new)
        if new:
            corpus = register_license(corpus, new)
            # NOTE: snapshot then log are two writes; a crash between them can drop the log line for
            # a persisted claim. The corpus-id dedup above makes the common desync self-correcting
            # (the claim is in the snapshot -> not re-registered). Full two-file atomicity is a v1
            # deferral (the store is explicitly a throwaway-able first pass — spec §8).
            self.root.mkdir(parents=True, exist_ok=True)
            self.corpus_path.write_text(dump_corpus(corpus))
            with self.log_path.open("a") as fh:
                fh.write("\n".join(ClaimLogRecord.of(c).model_dump_json() for c in new) + "\n")
        return AccumulateResult(len(proposed), len(new), len(proposed) - len(new), corpus)

    def census(self, corpus: Corpus | None = None) -> Census:
        """Coverage census over the current snapshot: (subject × modality) -> {status: count},
        plus the empty cells among observed subjects/modalities (the morphospace coverage frontier).
        Status is read CURRENT from the corpus; modality is derived via the B1 registry."""
        corpus = corpus if corpus is not None else self.load_corpus()
        cells: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
        subjects: set[str] = set()
        modalities: set[str] = set()
        for c in corpus.claims:
            sk = _subject_key(c)
            subjects.add(sk)
            mods = [m.value for m in claim_modalities(c)] or [_MODALITY_NONE]
            for m in mods:
                modalities.add(m)
                cells[(sk, m)][c.status.value] += 1
        gaps = tuple(
            (s, m)
            for s in sorted(subjects)
            for m in sorted(modalities)
            if (s, m) not in cells
        )
        return Census(
            cells={k: dict(v) for k, v in cells.items()},
            subjects=tuple(sorted(subjects)),
            modalities=tuple(sorted(modalities)),
            coverage_gaps=gaps,
        )
