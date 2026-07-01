# scripts/import_formal_claim_ir.py
"""Import a formal-claim-IR corpus (schema §13, v1.x) into a polymer-claims Corpus JSON.

General importer: point it at one or more `claims/` directories of formal-claim-IR JSON files and it
emits a polymer-claims Corpus (loadable via `serve --seed-corpus`, `load_corpus`). PolymerGenomics was
the first external source used to validate the migration path; nothing below is specific to it.

Honest transform (prototype-grade — the mapping is a projection, not a faithful round-trip):
  * status: outcome=negative OR evaluation verdict=REJECTED -> rejected(refuted); everything else ->
    conjectured. NOTHING is stamped `licensed`: a migrated claim has not passed THIS system's gate
    (the WITNESSED discipline — foreign claims land in the universe but earn no belief here).
  * one `quantity` leaf per claim from the headline statistic (mean of a list-valued stat);
    measurement_basis=derived + generating `formula`, never a false unit.
  * pattern: the grammar registry currently exposes a single pattern -> every claim uses
    adjusted_effect/v1 (deliberately coarse; richer typing needs more patterns in the grammar).
  * edges: genuine `depends_on` -> equivalence (severity 0.7). Each --source folder is a topic group
    whose members are chained by a low-severity thematic equivalence (0.3, status=structural) so the
    eigenmap has connected components per topic. No defeat edge is fabricated.

Regenerate the PolymerGenomics reference seed (data/demo/polymergenomics_universe.json):

  PG=/Users/zbb2/Desktop/PolymerGenomicsAPI/internal/InSilico
  .venv/bin/python scripts/import_formal_claim_ir.py --validate \
    --source "$PG/HLA experiment/claims" \
    --source "$PG/TE surveillance/claims" \
    --source "$PG/recombination hotspots/claims" \
    --source "$PG/dual_channel/claims" \
    --source "$PG/RC/01_methylome_capacity/claims" \
    --out data/demo/polymergenomics_universe.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter


def _headline_value(stats: list) -> tuple[float, str]:
    """The claim's primary numeric anchor. List-valued stats collapse to their mean."""
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
    base = os.path.basename(os.path.normpath(source_dir))
    if base == "claims":
        return os.path.basename(os.path.dirname(os.path.normpath(source_dir)))
    return base


def build_corpus(sources: list[str]) -> dict:
    claims: list[dict] = []
    equivalences: list[dict] = []
    groups: dict[str, list[str]] = {}
    idset: set[str] = set()

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

            claims.append({
                "schema_version": "v1.3",
                "id": stem,
                "title": title[:200],
                "pattern": {"id": "adjusted_effect", "version": "v1"},
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

    # thematic scaffold: chain members within each topic group (singletons stay isolated)
    for label, members in groups.items():
        members = [m for m in members if m in idset]
        for a, b in zip(members, members[1:]):
            equivalences.append({
                "id": f"eq_grp_{a[:10]}_{b[:10]}", "left": a, "right": b,
                "severity": 0.3, "status": "structural", "pending_reason": None,
                "note": f"thematic topic ({label})",
            })

    # keep only edges whose endpoints exist; de-duplicate edge ids
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
        "_groups": {k: len(v) for k, v in groups.items()},  # stripped before write
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", action="append", required=True, metavar="DIR",
                    help="a formal-claim-IR claims/ directory (repeatable)")
    ap.add_argument("--out", required=True, help="output Corpus JSON path")
    ap.add_argument("--validate", action="store_true",
                    help="validate the result against polymer_claims.io.load_corpus before writing")
    args = ap.parse_args()

    corpus = build_corpus(args.source)
    groups = corpus.pop("_groups")

    text = json.dumps(corpus, indent=1)
    if args.validate:
        import tempfile
        from polymer_claims.io import load_corpus
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            tf.write(text)
            tmp = tf.name
        c = load_corpus(tmp)
        os.unlink(tmp)
        print(f"validated ✓ ({len(c.claims)} claims against the Corpus model)")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(text)

    st = Counter(c["status"] for c in corpus["claims"])
    print(f"claims: {len(corpus['claims'])}  {dict(st)}")
    print(f"equivalences: {len(corpus['equivalences'])}  defeat_edges: 0")
    print(f"topic groups: {groups}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
