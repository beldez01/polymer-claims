# Rationale follow-ups (extending the first pass)

The `2026-06` first pass persists an LLM's free-text `rationale` ("why this claim was
proposed") as an additive, display-only field on `Provenance.rationale`
(`grammar/src/polymer_grammar/provenance.py`). It is preserved through the
untrusted-generation guardrail (`compile_untrusted` in
`protocol/src/polymer_protocol/generation_adapter.py`), set from the DSL in the umbrella
LLM adapter, and emitted top-level by `claim_detail`. It is OPAQUE: not validated, not
structured, not linked to any corpus claim. That is intentional for v1; this note lists
the rigorous extension.

## (a) Structure the rationale
- Replace the free-text string with `premises: tuple[str, ...]` + `builds_on: tuple[ClaimId, ...]`
  (the existing corpus claim ids the agent reasoned from), keeping a `summary` for display.
- Validate `builds_on` ids resolve in the corpus at integration time.

## (b) Link to the generative context / derivation graph
- Tie the rationale to the real `frontier` + the corpus snapshot the proposer saw, so the
  justification is a node in an auditable derivation graph (which claims + open frontier
  produced this claim), not an unanchored assertion.

## (c) Validation — anti-hallucinated-justification
- Length / size bounds; reject empty-after-strip (already coerced to `None`).
- Check the rationale actually corresponds to the claim it justifies (subject/conclusion
  overlap; cited `builds_on` claims are topically related) — catch fabricated cites.
- Consider routing the rationale itself through untrusted-generation scrutiny so a
  hallucinated justification cannot ride in unchecked alongside the claim.

## (d) Promote out of Provenance metadata
- If a rationale earns evidential weight (e.g. its premises become testable), promote it
  from `Provenance` metadata to a first-class epistemic field on `Claim`, and feed it into
  rival generation / critique (a rival can attack the stated premises, not just the
  conclusion). At that point it stops being "display only" and `compile_untrusted` must
  treat it with trust semantics rather than as benign descriptive text.
