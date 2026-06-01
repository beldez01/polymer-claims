"""Preliminary sensitivity test: ingest the frozen v1.2 corpus into the v1.3 grammar.

NOT production. A diagnostic probe whose VALUE is the gap report: for each real v1.2
claim it attempts a best-effort construction of a v1.3 `Claim` (phases 1-4) and records
(a) which v1.2 fields find a v1.3 home, (b) which are "homeless" (no slot yet), and
(c) whether a Claim is constructible at all. The homeless set is the concrete input to
the remaining grammar phases.

Reads v1.2 claim JSON as *data* only — does NOT import polymer_formalclaim, so the
grammar isolation guard is respected. Run: `cd grammar && uv run python scripts/probe_v12_ingest.py`
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, PropositionLeaf, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.proposition import Direction, Proposition
from polymer_grammar.status import PendingReason, Status

REPO = Path(__file__).resolve().parents[2]
CLAIMS_DIR = REPO / "v1.2" / "corpus" / "domains"

# v1.2 top-level fields and where (if anywhere) they land in the v1.3 grammar today.
# "—" marks a field with NO v1.3 home in phases 1-4 (the gap set).
FIELD_HOME = {
    "id": "Claim.id",
    "title": "Claim.title",
    "schema_version": "Claim.schema_version",
    "domain": "— (was the v1.2 domain axis; v1.3 replaces with pattern+profile)",
    "subject": "— (no Claim.subject slot built yet)",
    "context": "— (assembly/context; no slot)",
    "premises": "— (data provenance; protocol phase 7 / evaluator phase 8)",
    "operations": "— (compute graph; evaluator phase 8)",
    "statistics": "Claim.leaves (scalars only)",
    "inference": "partial -> Proposition + PropositionLeaf.warrant",
    "conclusion": "partial -> Proposition (free-text, lossy)",
    "depends_on": "— (-> L3 defeat/support edges or equivalence)",
    "external_assumptions": "— (Duhem auxiliaries -> L3 blame-sets, phase 5)",
    "version": "— (could map to MaterializationContext, phase 3 licensing)",
    "posted_at": "— (provenance metadata)",
    "api_version": "MaterializationContext.api_version (licensing)",
    "data_version": "MaterializationContext.data_version (licensing)",
    "exp_number": "— (provenance metadata)",
    "notebook": "— (provenance metadata)",
}

OUTCOME_TO_STATUS = {
    "positive": Status.LICENSED,
    "qualified_positive": Status.LICENSED,
    "negative": Status.REJECTED,
    "falsified": Status.REJECTED,
    "null": Status.PENDING,
    "exploratory": Status.EXPLORATORY,
}
OUTCOME_TO_DIRECTION = {
    "positive": Direction.POSITIVE,
    "qualified_positive": Direction.POSITIVE,
    "negative": Direction.NEGATIVE,
    "falsified": Direction.NEGATIVE,
    "null": Direction.NULL,
}


def _leaves_from_statistics(stats: list[dict]) -> tuple[list, list[str]]:
    """Scalar statistics -> QuantityLeaf. Returns (leaves, notes-on-unmappable)."""
    leaves, notes = [], []
    for s in stats or []:
        val = s.get("value")
        name = s.get("name", s.get("id", "stat"))
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            leaves.append(
                QuantityLeaf(
                    value=float(val),
                    measurement_basis=MeasurementBasis.DERIVED,
                    formula=name,
                )
            )
        elif isinstance(val, list):
            notes.append(f"vector-valued statistic {name!r} (n={len(val)}) has no single-Leaf home")
        else:
            notes.append(f"statistic {name!r} value type {type(val).__name__} unmapped")
    return leaves, notes


def probe(path: Path) -> dict:
    raw = json.loads(path.read_text())
    present = [k for k in raw if k in FIELD_HOME]
    homeless = [k for k in present if FIELD_HOME[k].startswith("—")]

    concl = raw.get("conclusion") or {}
    outcome = (concl.get("outcome") or "").lower()
    status = OUTCOME_TO_STATUS.get(outcome, Status.PENDING)
    direction = OUTCOME_TO_DIRECTION.get(outcome, Direction.NULL)

    leaves, leaf_notes = _leaves_from_statistics(raw.get("statistics", []))

    # Fall back to a PropositionLeaf carrying the qualitative conclusion (Toulmin warrant)
    # so a claim with only vector/no scalar statistics is still constructible.
    assertion = concl.get("assertion")
    justification = (raw.get("inference") or {}).get("justification")
    if assertion:
        leaves.append(
            PropositionLeaf(
                data=assertion[:500],
                warrant=(justification or "v1.2 inference expression")[:500],
                warrant_type="expert_judgment",
            )
        )

    result = {
        "file": str(path.relative_to(REPO)),
        "present_fields": present,
        "homeless_fields": homeless,
        "outcome": outcome,
        "n_scalar_leaves": sum(1 for l in leaves if getattr(l, "kind", "") == "quantity"),
        "leaf_notes": leaf_notes,
        "constructed": False,
        "error": None,
    }

    try:
        conclusion = None
        if assertion:
            conclusion = Proposition(
                direction=direction,
                estimand="UNKNOWN_v12_has_no_pattern",
                descriptor=raw.get("title", "")[:300] or "v1.2 claim",
            )
        Claim(
            id=raw.get("id") or path.stem,
            title=raw.get("title") or path.stem,
            pattern=PatternRef(id="ingested_unknown", version="v0"),
            leaves=tuple(leaves) if leaves else (),
            status=status,
            pending_reason=PendingReason.UNTESTED if status == Status.PENDING else None,
            conclusion=conclusion,
        )
        result["constructed"] = True
    except Exception as e:  # noqa: BLE001 - diagnostic: capture every failure reason
        result["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return result


def main() -> None:
    files = sorted(
        p for p in CLAIMS_DIR.rglob("*.json")
        if "/claims/" in p.as_posix() and not p.name.endswith(".evaluation.json")
    )
    results = [probe(p) for p in files]
    n = len(results)
    built = sum(r["constructed"] for r in results)

    homeless_counter = Counter()
    for r in results:
        homeless_counter.update(r["homeless_fields"])
    leaf_note_counter = Counter()
    for r in results:
        for note in r["leaf_notes"]:
            leaf_note_counter[note.split(" ", 2)[-1] if False else note.split("'")[0].strip()] += 1
    no_scalar = sum(1 for r in results if r["n_scalar_leaves"] == 0)
    errors = [r for r in results if not r["constructed"]]

    print(f"\n{'='*70}\nv1.2 -> v1.3 INGESTION SENSITIVITY PROBE\n{'='*70}")
    print(f"claims found:            {n}")
    print(f"v1.3 Claim constructible: {built}/{n}  ({100*built//max(n,1)}%)")
    print(f"claims with 0 scalar leaves (lean on PropositionLeaf fallback): {no_scalar}/{n}")

    print(f"\n--- HOMELESS v1.2 FIELDS (no v1.3 slot in phases 1-4) ---")
    for field, cnt in homeless_counter.most_common():
        print(f"  {cnt:3d}/{n}  {field:22s} -> {FIELD_HOME[field]}")

    print(f"\n--- STATISTICS THAT DON'T FIT A SINGLE LEAF ---")
    total_vec = sum(c for k, c in leaf_note_counter.items())
    print(f"  {total_vec} unmappable statistic instances across the corpus, e.g.:")
    for note, cnt in leaf_note_counter.most_common(6):
        print(f"    {cnt:3d}x  {note}")

    if errors:
        print(f"\n--- CONSTRUCTION FAILURES ({len(errors)}) ---")
        for r in errors[:15]:
            print(f"  {r['file'].split('/')[-1]}: {r['error']}")

    print(f"\n--- READING ---")
    print("  Constructible != faithful. A built Claim still drops subject, premises,")
    print("  operations, external_assumptions, depends_on, and vector statistics, and")
    print("  fabricates a placeholder pattern + estimand. Those are the real gaps.")


if __name__ == "__main__":
    main()
