"""Faithful v1.2 -> v1.3 re-ingest (closes the loop on probe_v12_ingest.py).

Unlike the first probe (which only checked field coverage), this MAPS each of the 47 v1.2
claims into a real v1.3 Claim — now including the freshly-built `Subject` slot — and reports
how faithfully the corpus is representable. The value is the report, not the code (NOT
production). Reads v1.2 JSON as data only (no polymer_formalclaim import).

Run: `cd grammar && uv run python scripts/reingest_v12.py`
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
from polymer_grammar.subject import (
    Cohort,
    CohortDefinition,
    CohortSourceDataset,
    CompositeSubject,
    LiteralSubject,
)

REPO = Path(__file__).resolve().parents[2]
CLAIMS_DIR = REPO / "v1.2" / "corpus" / "domains"

OUTCOME_TO_STATUS = {
    "positive": Status.LICENSED, "qualified_positive": Status.LICENSED,
    "negative": Status.REJECTED, "falsified": Status.REJECTED,
    "null": Status.PENDING, "exploratory": Status.EXPLORATORY,
}
OUTCOME_TO_DIRECTION = {
    "positive": Direction.POSITIVE, "qualified_positive": Direction.POSITIVE,
    "negative": Direction.NEGATIVE, "falsified": Direction.NEGATIVE, "null": Direction.NULL,
}
_VALID_RELATIONS = {
    "co_occurrence", "conditional", "causal_hypothesis", "temporal_sequence", "correlational",
}

# v1.2 top-level field -> where it lands in v1.3 NOW (after subject + L3 + L4 + FDR).
FIELD_HOME = {
    "id": "Claim.id", "title": "Claim.title", "schema_version": "Claim.schema_version",
    "subject": "Claim.subject  ✅ (NEW)",
    "statistics": "Claim.leaves (scalars)",
    "conclusion": "partial -> Proposition",
    "inference": "partial -> Proposition / warrant",
    "domain": "— (replaced by pattern + profile)",
    "context": "— (assembly; no slot)",
    "premises": "— (provenance; Phase 7 #1/#3 + Phase 8)",
    "operations": "— (compute graph; Phase 8 evaluator)",
    "depends_on": "— (-> L3 defeat/equivalence at corpus level)",
    "external_assumptions": "— (Duhem auxiliaries; first-class node still TODO)",
    "version": "— (-> MaterializationContext, licensing)",
    "posted_at": "— (provenance metadata)",
    "api_version": "MaterializationContext.api_version",
    "data_version": "MaterializationContext.data_version",
    "exp_number": "— (provenance metadata)",
    "notebook": "— (provenance metadata)",
}


def _pairs(d):
    return tuple((str(k), str(v)) for k, v in d.items()) if isinstance(d, dict) else ()


def map_subject(s):
    """Map a v1.2 subject dict into a v1.3 Subject (cohort/literal/composite). Returns the
    Subject or raises (caller records the failure)."""
    kind = s.get("kind")
    base = dict(id=s.get("id", "unknown"), display=s.get("display", "")[:300] or "subject")
    if s.get("note"):
        base["note"] = s["note"][:300]
    if kind == "cohort":
        d = s.get("definition") or {}
        sd = d.get("source_dataset")
        source = None
        if sd:
            source = CohortSourceDataset(
                name=sd.get("name", "unknown"), version=sd.get("version"), tissue=sd.get("tissue")
            )
        return Cohort(
            **base, members_hash=s.get("members_hash", "unknown"),
            definition=CohortDefinition(
                source_dataset=source,
                inclusion=tuple(str(x) for x in d.get("inclusion", [])),
                exclusion=tuple(str(x) for x in d.get("exclusion", [])),
                cardinality=d.get("cardinality"), random_seed=d.get("random_seed"),
            ),
        )
    if kind == "literal":
        return LiteralSubject(**base, prose=s.get("prose", "")[:500] or "(none)",
                              structured=_pairs(s.get("structured")))
    if kind == "composite":
        parts = tuple(map_subject(p) for p in s.get("parts", []))
        relation = s.get("relation")
        if relation not in _VALID_RELATIONS:
            relation = "correlational"
        return CompositeSubject(**base, parts=parts, relation=relation)
    raise ValueError(f"unmapped subject kind: {kind!r}")


def _leaves(stats):
    leaves, vec = [], 0
    for s in stats or []:
        v, name = s.get("value"), s.get("name", s.get("id", "stat"))
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            leaves.append(QuantityLeaf(value=float(v),
                          measurement_basis=MeasurementBasis.DERIVED, formula=name))
        elif isinstance(v, list):
            vec += 1
    return leaves, vec


def reingest(path):
    raw = json.loads(path.read_text())
    present = [k for k in raw if k in FIELD_HOME]
    homeless = [k for k in present if FIELD_HOME[k].startswith("—")]
    out = {"file": path.name, "homeless": homeless, "subject_kind": None,
           "subject_mapped": False, "constructed": False, "vec_stats": 0, "error": None}

    # subject
    subj = None
    s = raw.get("subject")
    if isinstance(s, dict):
        out["subject_kind"] = s.get("kind")
        try:
            subj = map_subject(s)
            out["subject_mapped"] = True
        except Exception as e:  # noqa: BLE001 - diagnostic
            out["error"] = f"subject: {type(e).__name__}: {str(e)[:120]}"

    concl = raw.get("conclusion") or {}
    outcome = (concl.get("outcome") or "").lower()
    status = OUTCOME_TO_STATUS.get(outcome, Status.PENDING)
    leaves, out["vec_stats"] = _leaves(raw.get("statistics", []))
    assertion = concl.get("assertion")
    if assertion:
        leaves.append(PropositionLeaf(data=assertion[:500], warrant="v1.2 inference",
                      warrant_type="expert_judgment"))
    try:
        conclusion = None
        if assertion:
            conclusion = Proposition(direction=OUTCOME_TO_DIRECTION.get(outcome, Direction.NULL),
                                     estimand="UNKNOWN_v12_pattern", descriptor=raw.get("title", "")[:300] or "v1.2")
        Claim(id=raw.get("id") or path.stem, title=raw.get("title") or path.stem,
              pattern=PatternRef(id="ingested_unknown", version="v0"),
              leaves=tuple(leaves) if leaves else (), status=status,
              pending_reason=PendingReason.UNTESTED if status == Status.PENDING else None,
              conclusion=conclusion, subject=subj)
        out["constructed"] = True
    except Exception as e:  # noqa: BLE001 - diagnostic
        out["error"] = out["error"] or f"claim: {type(e).__name__}: {str(e)[:120]}"
    return out


def main():
    files = sorted(p for p in CLAIMS_DIR.rglob("*.json")
                   if "/claims/" in p.as_posix() and not p.name.endswith(".evaluation.json"))
    results = [reingest(p) for p in files]
    n = len(results)
    built = sum(r["constructed"] for r in results)
    subj_present = sum(1 for r in results if r["subject_kind"])
    subj_mapped = sum(r["subject_mapped"] for r in results)
    by_kind = Counter(r["subject_kind"] for r in results if r["subject_kind"])
    homeless = Counter()
    for r in results:
        homeless.update(r["homeless"])
    vec_total = sum(r["vec_stats"] for r in results)
    errors = [r for r in results if r["error"]]

    print(f"\n{'='*70}\nFAITHFUL v1.2 -> v1.3 RE-INGEST (post subject-slot)\n{'='*70}")
    print(f"claims:                       {n}")
    print(f"v1.3 Claim constructible:     {built}/{n}  ({100*built//max(n,1)}%)")
    print(f"claims with a v1.2 subject:   {subj_present}/{n}")
    print(f"  -> mapped into v1.3 Subject: {subj_mapped}/{subj_present}  "
          f"({100*subj_mapped//max(subj_present,1)}%)  ⬅ the NEW capability")
    print(f"  subject kinds: {dict(by_kind)}")
    print("\n--- STILL-HOMELESS v1.2 fields (no v1.3 home yet) ---")
    for field, cnt in homeless.most_common():
        print(f"  {cnt:3d}/{n}  {field:22s} -> {FIELD_HOME[field]}")
    print(f"\n--- vector-valued statistics still unmapped: {vec_total} (the L0 vector-Leaf gap) ---")
    if errors:
        print(f"\n--- ERRORS ({len(errors)}) ---")
        for r in errors[:10]:
            print(f"  {r['file']}: {r['error']}")
    print("\n--- READING ---")
    print("  Subject now has a home (was 47/47 homeless in the first probe). Remaining")
    print("  homeless fields are provenance (Phase 7 #1/#3), the compute graph (Phase 8),")
    print("  and Duhem auxiliaries; vector statistics still need an L0 vector-Leaf. The")
    print("  pattern/estimand are still placeholders (no claim->pattern classifier yet).")


if __name__ == "__main__":
    main()
