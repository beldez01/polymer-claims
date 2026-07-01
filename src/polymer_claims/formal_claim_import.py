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


def build_corpus_dict(sources: Iterable[str | os.PathLike], *, sheaf_active: bool = False) -> dict:
    """Transform formal-claim-IR JSON directories into a Corpus-shaped dict (unvalidated).

    sheaf_active=False (default): the honest un-laundered WITNESSED view — non-negatives are
    ``conjectured``, leaves keep their signed value and ``dimension=None``, and all equivalence
    edges are ``structural`` (so nothing enters the sheaf gauge).

    sheaf_active=True: make the universe project in the sheaf gauge, honestly:
      * leaf value -> abs(value); dimension -> dimensionless {exponents: []} (commensurable);
      * non-negatives -> ``pending`` (untested) so they clear the {licensed, pending} sheaf filter
        (negatives stay ``rejected``; nothing is ever ``licensed``);
      * genuine ``depends_on`` edges -> ``pending`` (feed layout AND sheaf); the thematic same-topic
        scaffold stays ``structural`` (feeds layout only — the sheaf never sees it, so it cannot
        fabricate tension).
    """
    sources = [os.fspath(s) for s in sources]
    claims: list[dict] = []
    equivalences: list[dict] = []
    groups: dict[str, list[str]] = {}
    idset: set[str] = set()

    # sheaf-active gates a depends_on edge into the sheaf ONLY when both claims share the same
    # headline quantity — so the gauge never equates non-comparable values (e.g. an AUROC with a
    # raw count). Pre-scan the headline formula per claim id to decide.
    formula_by_id: dict[str, str] = {}
    if sheaf_active:
        for src in sources:
            for f in sorted(glob.glob(os.path.join(src, "*.json"))):
                if f.endswith(".evaluation.json"):
                    continue
                dd = json.load(open(f))
                _, sn = _headline_value(dd.get("statistics") or [])
                formula_by_id[os.path.basename(f)[:-5]] = f"migrated::{sn}"

    for src in sources:
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

            if is_neg:
                status, pending_reason, rejection_reason = "rejected", None, "refuted"
            elif sheaf_active:
                status, pending_reason, rejection_reason = "pending", "untested", None
            else:
                status, pending_reason, rejection_reason = "conjectured", None, None

            leaf_value = abs(float(val)) if sheaf_active else float(val)
            leaf_dimension = {"exponents": []} if sheaf_active else None

            claims.append({
                "schema_version": "v1.3",
                "id": stem,
                "title": title[:200],
                "pattern": dict(_ADJUSTED_EFFECT),
                "leaves": [{
                    "kind": "quantity", "value": round(leaf_value, 6), "unit": None,
                    "uncertainty": None, "measurement_basis": "derived",
                    "formula": f"migrated::{statname}", "dimension": leaf_dimension,
                }],
                "status": status,
                "pending_reason": pending_reason,
                "rejection_reason": rejection_reason,
                "strength": None, "conclusion": None, "licensing": None, "roles": None,
                "subject": None, "provenance": None, "governance": None,
                "evaluation_plan": None, "representation_revision": None,
            })
            idset.add(stem)
            groups.setdefault(label, []).append(stem)

            # genuine depends_on -> a layout edge; sheaf-eligible (pending) ONLY when the two claims
            # share the same headline quantity (else it would equate non-comparable values).
            for dep in (d.get("depends_on") or []):
                same_q = (
                    sheaf_active
                    and formula_by_id.get(stem) is not None
                    and formula_by_id.get(stem) == formula_by_id.get(dep)
                )
                equivalences.append({
                    "id": f"eq_dep_{stem[:10]}_{dep[:10]}", "left": stem, "right": dep,
                    "severity": 0.7,
                    "status": "pending" if same_q else "structural",
                    "pending_reason": "untested" if same_q else None,
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


def import_formal_claim_ir(
    sources: Iterable[str | os.PathLike], *, sheaf_active: bool = False
) -> Corpus:
    """Import one or more formal-claim-IR `claims/` directories into a validated `Corpus`."""
    return Corpus.model_validate(build_corpus_dict(sources, sheaf_active=sheaf_active))
