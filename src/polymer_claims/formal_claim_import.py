"""Formal-claim-IR ingestion — foreign formal claims -> a polymer-claims `Corpus`.

Mirrors `attested_ingest` in spirit (an impure umbrella that folds an external source into the
corpus) but for PRIMARY RESULTS rather than testimony. Point it at one or more formal-claim-IR
`claims/` directories (schema §13, v1.x); it returns a validated `Corpus`.

The load-bearing rule is the WITNESSED discipline: an imported claim enters the universe but is
NEVER `licensed` — it has not passed THIS system's gate. Concretely:
  * outcome=negative OR evaluation verdict=REJECTED -> REJECTED (rejection_reason=refuted)
  * everything else                                 -> CONJECTURED
The transform is a projection, not a faithful round-trip:
  * one `quantity` leaf per claim from the headline statistic (mean of a list-valued stat),
    measurement_basis=derived + generating `formula`, never a false unit;
  * the grammar registry currently exposes one pattern -> every claim uses adjusted_effect/v1;
  * genuine `depends_on` -> equivalence(0.7); each source folder is a topic group whose members
    are chained by a low-severity thematic equivalence(0.3, structural) so the eigenmap has
    connected components. No defeat edge is fabricated.
"""
from __future__ import annotations

import glob
import json
import os
from collections.abc import Iterable

from polymer_protocol import Corpus

_ADJUSTED_EFFECT = {"id": "adjusted_effect", "version": "v1"}


def _headline_value(stats: list) -> tuple[float, str]:
    """The claim's primary numeric anchor; a list-valued statistic collapses to its mean."""
    if not stats:
        return 0.0, "n/a"
    s0 = stats[0]
    name = s0.get("name") or "stat"
    v = s0.get("value")
    if isinstance(v, list):
        nums = [x.get("value") for x in v if isinstance(x.get("value"), (int, float))]
        return (sum(nums) / len(nums) if nums else 0.0), name
    if isinstance(v, (int, float)):
        return float(v), name
    return 0.0, name


def _group_label(source_dir: str) -> str:
    """A human label for a claims dir; `.../<topic>/claims` -> `<topic>`."""
    norm = os.path.normpath(source_dir)
    base = os.path.basename(norm)
    return os.path.basename(os.path.dirname(norm)) if base == "claims" else base


def build_corpus_dict(sources: Iterable[str | os.PathLike]) -> dict:
    """Transform formal-claim-IR JSON directories into a Corpus-shaped dict (unvalidated)."""
    claims: list[dict] = []
    equivalences: list[dict] = []
    groups: dict[str, list[str]] = {}
    idset: set[str] = set()

    for src in sources:
        src = os.fspath(src)
        label = _group_label(src)
        for f in sorted(glob.glob(os.path.join(src, "*.json"))):
            if f.endswith(".evaluation.json"):
                continue
            d = json.load(open(f))
            stem = os.path.basename(f)[:-5]
            title = d.get("title") or stem
            outcome = (d.get("conclusion") or {}).get("outcome")
            verdict = None
            evp = f.replace(".json", ".evaluation.json")
            if os.path.exists(evp):
                try:
                    verdict = json.load(open(evp)).get("verdict")
                except Exception:
                    pass
            val, statname = _headline_value(d.get("statistics") or [])
            is_neg = (outcome == "negative") or (verdict == "REJECTED")

            claims.append({
                "schema_version": "v1.3",
                "id": stem,
                "title": title[:200],
                "pattern": dict(_ADJUSTED_EFFECT),
                "leaves": [{
                    "kind": "quantity", "value": round(float(val), 6), "unit": None,
                    "uncertainty": None, "measurement_basis": "derived",
                    "formula": f"migrated::{statname}", "dimension": None,
                }],
                "status": "rejected" if is_neg else "conjectured",
                "pending_reason": None,
                "rejection_reason": "refuted" if is_neg else None,
                "strength": None, "conclusion": None, "licensing": None, "roles": None,
                "subject": None, "provenance": None, "governance": None,
                "evaluation_plan": None, "representation_revision": None,
            })
            idset.add(stem)
            groups.setdefault(label, []).append(stem)

            for dep in (d.get("depends_on") or []):
                equivalences.append({
                    "id": f"eq_dep_{stem[:10]}_{dep[:10]}", "left": stem, "right": dep,
                    "severity": 0.7, "status": "structural", "pending_reason": None,
                    "note": "migrated depends_on",
                })

    for label, members in groups.items():
        members = [m for m in members if m in idset]
        for a, b in zip(members, members[1:]):
            equivalences.append({
                "id": f"eq_grp_{a[:10]}_{b[:10]}", "left": a, "right": b,
                "severity": 0.3, "status": "structural", "pending_reason": None,
                "note": f"thematic topic ({label})",
            })

    equivalences = [e for e in equivalences if e["left"] in idset and e["right"] in idset]
    seen: set[str] = set()
    for e in equivalences:
        while e["id"] in seen:
            e["id"] += "_x"
        seen.add(e["id"])

    return {
        "claims": claims,
        "defeat_edges": [],
        "equivalences": equivalences,
        "fdr_ledger": {"target_fdr": 0.05, "procedure": "elond", "tests": []},
    }


def import_formal_claim_ir(sources: Iterable[str | os.PathLike]) -> Corpus:
    """Import one or more formal-claim-IR `claims/` directories into a validated `Corpus`."""
    return Corpus.model_validate(build_corpus_dict(sources))
