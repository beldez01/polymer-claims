"""The first real-intelligence GENERATION adapter: maps a small constrained DSL emitted by an
injected language model into a valid EXECUTABLE grammar Claim.

Honesty caveat: v1 plans use builtin::const — the only impl the reference adapters execute — so
the value+threshold are LLM-asserted. This proves the plumbing (real generation → executable →
license) end-to-end, but the execution substrate is the deterministic reference adapters, NOT real
data. Meaningful data execution is gated on real execution adapters (a separate arc).
compile_untrusted forces AGENT_GENERATED provenance so generated claims are always distinguishable.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    SatisfactionCriterion,
    Status,
)
from polymer_protocol import Corpus, Proposal

_COMPARATORS = {
    "lt": Comparator.LT,
    "le": Comparator.LE,
    "gt": Comparator.GT,
    "ge": Comparator.GE,
    "eq": Comparator.EQ,
    "ne": Comparator.NE,
}
_GEN_PREFIX = "gen-llm-"


class LLMGenerationAdapter:
    """A GenerationAdapter whose proposals come from an injected `complete` (real model OUTSIDE
    the pure core). Maps a constrained DSL into executable PENDING+plan grammar Claims."""

    def __init__(
        self,
        complete: Callable[[str], str],
        *,
        identity: str = "llm-claim-proposer",
        max_proposals: int = 5,
        allowed_patterns: tuple[str, ...] | None = None,
    ) -> None:
        self.complete = complete
        self.identity = identity
        self.max_proposals = max_proposals
        self.allowed_patterns = allowed_patterns  # None => any non-empty pattern_id

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        raw = self.complete(self._build_prompt(corpus, frontier))
        return self._parse(raw, corpus)

    # --- pure helpers ---
    def _build_prompt(self, corpus: Corpus, frontier: tuple[str, ...]) -> str:
        lines = []
        for c in sorted(corpus.claims, key=lambda c: c.id)[:20]:
            concl = getattr(c.conclusion, "descriptor", None)
            lines.append(
                f"- {c.id} [{c.pattern.id}] {c.title}" + (f" :: {concl}" if concl else "")
            )
        existing = "\n".join(lines) or "(none)"
        front = ", ".join(frontier) or "(none)"
        schema = (
            '{"proposals":[{"title":str,"pattern_id":str,"ontology_term":str,'
            '"value":number,"comparator":"lt|le|gt|ge|eq|ne","threshold":number,'
            '"rationale":str}]}'
        )
        return (
            "You are a scientific-claim generator. Propose up to "
            f"{self.max_proposals} NOVEL, testable claims that extend the corpus below. "
            "Do NOT restate existing claims. Return STRICT JSON ONLY, no prose, matching:\n"
            f"{schema}\n"
            "value and threshold are numbers; comparator is one of lt,le,gt,ge,eq,ne.\n\n"
            f"Existing claims:\n{existing}\n\nUnresolved frontier: {front}\n"
        )

    def _parse(self, raw: str, corpus: Corpus) -> tuple[Proposal, ...]:
        obj = _extract_json(raw)
        if obj is None:
            return ()
        existing_ids = set(corpus.by_id().keys())
        out: list[Proposal] = []
        seen: set[str] = set()
        for p in obj.get("proposals", []):
            try:
                claim = self._build_claim(p)
            except (KeyError, ValueError, TypeError):
                continue
            if claim.id in existing_ids or claim.id in seen:
                continue  # convergence / dedup (own outputs already in corpus skipped here)
            seen.add(claim.id)
            out.append(Proposal(operator_id=self.identity, claim=claim))
            if len(out) >= self.max_proposals:
                break
        return tuple(out)

    def _build_claim(self, p: dict) -> Claim:
        title = str(p["title"]).strip()
        pattern_id = str(p["pattern_id"]).strip()
        ontology_term = str(p["ontology_term"]).strip()
        cmp_key = str(p["comparator"]).strip().lower()
        if not (title and pattern_id and ontology_term):
            raise ValueError("empty required field")
        if self.allowed_patterns is not None and pattern_id not in self.allowed_patterns:
            raise ValueError("disallowed pattern")
        if cmp_key not in _COMPARATORS:
            raise ValueError("bad comparator")
        value = float(p["value"])  # raises -> dropped
        threshold = float(p["threshold"])
        cid = _GEN_PREFIX + hashlib.sha256(
            f"{title}|{pattern_id}|{ontology_term}|{value}|{cmp_key}|{threshold}".encode()
        ).hexdigest()[:16]
        node = OperationNode(
            id="n0",
            impl="builtin::const",
            params=(("value", str(value)),),
            produces=ProducedLeafSpec(
                leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED
            ),
        )
        plan = EvaluationPlan(
            graph=ComputeGraph(nodes=(node,), terminal="n0"),
            criterion=SatisfactionCriterion(
                comparator=_COMPARATORS[cmp_key], threshold=threshold
            ),
        )
        return Claim(
            id=cid,
            title=title,
            pattern=PatternRef(id=pattern_id, version="v1"),
            leaves=(CategoricalLeaf(ontology_term=ontology_term),),
            status=Status.PENDING,
            pending_reason=PendingReason.UNTESTED,
            strength=None,
            evaluation_plan=plan,
        )

    @classmethod
    def anthropic(
        cls,
        *,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        **kw,
    ) -> "LLMGenerationAdapter":
        """Build an adapter backed by the Anthropic SDK (needs the [llm] extra). Lazy import."""
        try:
            import anthropic
        except ModuleNotFoundError as e:  # pragma: no cover - exercised via CLI, not unit tests
            raise RuntimeError(
                "the LLM adapter needs the optional extra: pip install 'polymer-claims[llm]'"
            ) from e
        client = anthropic.Anthropic(api_key=api_key)

        def complete(prompt: str) -> str:  # pragma: no cover - real network
            msg = client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(getattr(b, "text", "") for b in msg.content)

        return cls(complete, **kw)


def _extract_json(raw: str) -> dict | None:
    """Best-effort: parse the first {...} object, tolerating code fences / surrounding prose."""
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        if s.lstrip().startswith("json"):
            s = s.lstrip()[4:]
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        obj = json.loads(s[start : end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None
