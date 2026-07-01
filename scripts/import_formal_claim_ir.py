# scripts/import_formal_claim_ir.py
"""Import a formal-claim-IR corpus (schema §13, v1.x) into a polymer-claims Corpus JSON.

Thin CLI wrapper over `polymer_claims.formal_claim_import` (the same logic backs the
`polymer-claims ingest-formal-claims` subcommand). Point it at one or more `claims/` directories
of formal-claim-IR JSON files; it emits a polymer-claims Corpus (loadable via `serve --seed-corpus`,
`load_corpus`). See the module docstring for the transform + the WITNESSED discipline (imported
claims are never `licensed`).

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
import json
import os
from collections import Counter

from polymer_claims.formal_claim_import import build_corpus_dict


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--source", action="append", required=True, metavar="DIR",
                    help="a formal-claim-IR claims/ directory (repeatable)")
    ap.add_argument("--out", required=True, help="output Corpus JSON path")
    ap.add_argument("--validate", action="store_true",
                    help="validate the result against the Corpus model before writing")
    args = ap.parse_args()

    corpus = build_corpus_dict(args.source)
    text = json.dumps(corpus, indent=1)

    if args.validate:
        from polymer_protocol import Corpus
        Corpus.model_validate(corpus)
        print(f"validated ✓ ({len(corpus['claims'])} claims against the Corpus model)")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(text)

    st = Counter(c["status"] for c in corpus["claims"])
    print(f"claims: {len(corpus['claims'])}  {dict(st)}")
    print(f"equivalences: {len(corpus['equivalences'])}  defeat_edges: {len(corpus['defeat_edges'])}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
