"""REPRESENT (deterministic part): build the VAF argumentation scaffolding.

Writes nothing. Computes the grounded extension over effective defeats and the
unresolved-attack frontier (effective-defeat targets that are NOT grounded). The
calibrated two-axis posterior and the cross-cycle 'newly-incident attack' set are
deferred (spec §6.1) — SELECT (#3) and the daemons (#5).
"""
from __future__ import annotations

from polymer_grammar import Status, effective_defeats, grounded_extension

from .corpus import Corpus, CycleScaffolding


def represent(corpus: Corpus) -> CycleScaffolding:
    claim_ids = [c.id for c in corpus.claims]
    id_set = set(claim_ids)
    strength = {c.id: c.strength for c in corpus.claims}
    licensed_ids = frozenset(c.id for c in corpus.claims if c.status == Status.LICENSED)
    grounded = grounded_extension(claim_ids, corpus.defeat_edges, strength, licensed_ids)
    defeats = effective_defeats(corpus.defeat_edges, strength, licensed_ids)
    frontier = {
        tgt for _src, tgt in defeats if tgt in id_set and tgt not in grounded
    }
    return CycleScaffolding(
        # grounded_extension() may include synthetic defeat-source node ids (e.g.
        # "refutation:<id>") that are not claims; intersect to keep only real claim ids.
        grounded_extension=tuple(sorted(grounded & id_set)),
        frontier=tuple(sorted(frontier)),
    )
