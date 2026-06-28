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
    GenerationMode,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    Provenance,
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
_MD_PREFIX = "gen-md-"
_METHYL_REGION_PREFIX = "gen-methyl-region-"
_METHYL_NDMP_PREFIX = "gen-methyl-ndmp-"


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
        proposals = obj.get("proposals")
        if not isinstance(proposals, list):
            return ()  # absent/null/non-list -> no proposals (degrade, don't crash)
        for p in proposals:
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
        # FIRST PASS: opaque free-text justification, display only. None when absent/empty.
        rationale = str(p["rationale"]).strip() if p.get("rationale") else None
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
            provenance=Provenance(
                generated_by=GenerationMode.AGENT_GENERATED,
                agent_id=self.identity,
                search_cardinality=1,
                rationale=rationale,
            ),
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


class MeanDiffGenerationAdapter:
    """A GenerationAdapter that maps an injected model's DSL into a REAL-DATA
    `stats::mean_diff` Claim over a bundled dataset (Phase 2b). Mirrors
    LLMGenerationAdapter but targets the real-execution substrate, not builtin::const."""

    def __init__(
        self,
        complete: Callable[[str], str],
        *,
        identity: str = "llm-meandiff-proposer",
        max_proposals: int = 5,
        dataset: str = "dose_response",
    ) -> None:
        self.complete = complete
        self.identity = identity
        self.max_proposals = max_proposals
        self.dataset = dataset

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        return self._parse(self.complete(self._build_prompt(corpus, frontier)), corpus)

    def _build_prompt(self, corpus: Corpus, frontier: tuple[str, ...]) -> str:
        from .datasets import load_dataset
        data = load_dataset(self.dataset)
        cols = ", ".join(data.keys())
        groups = ", ".join(sorted(set(data["dose"]))) if "dose" in data else "(unknown)"
        lines = [
            f"- {c.id} [{c.pattern.id}] {c.title}"
            for c in sorted(corpus.claims, key=lambda c: c.id)[:20]
        ]
        existing = "\n".join(lines) or "(none)"
        schema = (
            '{"proposals":[{"title":str,"value_col":str,"group_col":str,"group_a":str,'
            '"group_b":str,"comparator":"lt|le|gt|ge|eq|ne","threshold":number,"rationale":str}]}'
        )
        return (
            "You are a scientific-claim generator working over a REAL dataset. Propose up to "
            f"{self.max_proposals} NOVEL, testable claims, each a two-group MEAN DIFFERENCE on "
            f"dataset '{self.dataset}'.\n"
            f"Columns: {cols}. A numeric value column is 'response'. Group column 'dose' has "
            f"groups: {groups}.\n"
            "Each claim asserts: mean(value_col | group_col==group_a) − mean(value_col | "
            "group_col==group_b) <comparator> threshold.\n"
            "Output ONLY the JSON object, no prose, no markdown, matching:\n"
            f"{schema}\n\n"
            f"Existing claims:\n{existing}\n\nUnresolved frontier: {', '.join(frontier) or '(none)'}\n"
        )

    def _parse(self, raw: str, corpus: Corpus) -> tuple[Proposal, ...]:
        obj = _extract_json(raw)
        if obj is None:
            return ()
        existing_ids = set(corpus.by_id().keys())
        out: list[Proposal] = []
        seen: set[str] = set()
        proposals = obj.get("proposals")
        if not isinstance(proposals, list):
            return ()  # absent/null/non-list -> no proposals (degrade, don't crash)
        for p in proposals:
            try:
                claim = self._build_claim(p)
            except (KeyError, ValueError, TypeError):
                continue
            if claim.id in existing_ids or claim.id in seen:
                continue
            seen.add(claim.id)
            out.append(Proposal(operator_id=self.identity, claim=claim))
            if len(out) >= self.max_proposals:
                break
        return tuple(out)

    def _build_claim(self, p: dict):
        from .datasets import load_dataset
        from .exec_adapters import mean_diff_claim
        title = str(p["title"]).strip()
        value_col = str(p["value_col"]).strip()
        group_col = str(p["group_col"]).strip()
        group_a = str(p["group_a"]).strip()
        group_b = str(p["group_b"]).strip()
        cmp_key = str(p["comparator"]).strip().lower()
        if cmp_key not in _COMPARATORS:
            raise ValueError("bad comparator")
        if not (title and value_col and group_col and group_a and group_b):
            raise ValueError("empty required field")
        if group_a == group_b:
            raise ValueError("groups must differ")
        threshold = float(p["threshold"])
        data = load_dataset(self.dataset)  # unknown dataset -> raises -> dropped
        if value_col not in data or group_col not in data:
            raise ValueError("unknown column")
        rationale = str(p["rationale"]).strip() if p.get("rationale") else None
        cid = _MD_PREFIX + hashlib.sha256(
            f"{title}|{value_col}|{group_col}|{group_a}|{group_b}|{cmp_key}|{threshold}".encode()
        ).hexdigest()[:16]
        return mean_diff_claim(
            cid,
            value_col=value_col,
            group_col=group_col,
            group_a=group_a,
            group_b=group_b,
            comparator=_COMPARATORS[cmp_key],
            threshold=threshold,
            ref=self.dataset,
            title=title,
            rationale=rationale,
        )

    @classmethod
    def anthropic(
        cls,
        *,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        **kw,
    ) -> "MeanDiffGenerationAdapter":
        """Build a real-data adapter backed by the Anthropic SDK (needs the [llm] extra)."""
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


class MethylGenerationAdapter:
    """A GenerationAdapter that maps an injected model's constrained DSL into executable
    methylation claims over SE-Contracts. This is Phase B's first slice: the agent can propose
    `region_delta_beta` and `n_dmps` claims, while the existing independent methylation legs and
    e-value/FDR gate decide whether anything licenses."""

    def __init__(
        self,
        complete: Callable[[str], str],
        *,
        identity: str = "llm-methyl-proposer",
        max_proposals: int = 5,
        refs: tuple[str, ...] | None = None,
        assets: tuple | None = None,
    ) -> None:
        self.complete = complete
        self.identity = identity
        self.max_proposals = max_proposals
        if assets is None:
            from .assets import methylation_asset_catalog
            assets = methylation_asset_catalog()
        self.assets = assets
        self.refs = refs if refs is not None else tuple(a.ref for a in assets)

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        return self._parse(self.complete(self._build_prompt(corpus, frontier)), corpus)

    def _build_prompt(self, corpus: Corpus, frontier: tuple[str, ...]) -> str:
        lines = [
            f"- {c.id} [{c.pattern.id}] {c.title}"
            for c in sorted(corpus.claims, key=lambda c: c.id)[:20]
        ]
        existing = "\n".join(lines) or "(none)"
        asset_lines = []
        for asset in self.assets:
            asset_lines.append(
                f"- {asset.ref}: {asset.label}; group_col={asset.group_col}; "
                f"levels={','.join(asset.levels)}; profile={asset.profile_id}; "
                f"ops={','.join(asset.operations)}"
            )
        refs = "\n".join(asset_lines) or ", ".join(self.refs)
        schema = (
            '{"proposals":[{"kind":"region_delta_beta|n_dmps","title":str,"ref":str,'
            '"group_col":"Sample_Group","level_a":str,"level_b":str,'
            '"region_probes":[str,...],"alpha":number,"k":number,'
            '"comparator":"lt|le|gt|ge|eq|ne","threshold":number,"rationale":str}]}'
        )
        return (
            "You are a scientific-claim generator working over methylation SE-Contracts. "
            f"Propose up to {self.max_proposals} NOVEL executable methylation claims.\n"
            f"Available assets:\n{refs}\n"
            "Allowed kinds: region_delta_beta (requires region_probes and threshold) or n_dmps "
            "(requires alpha and k). Use group_col Sample_Group unless the asset metadata says "
            "otherwise. For IDH AML contrasts use level_a WT and level_b IDH_mut; for fixtures use "
            "level1 and level2. Output ONLY strict JSON matching:\n"
            f"{schema}\n\n"
            f"Existing claims:\n{existing}\n\nUnresolved frontier: {', '.join(frontier) or '(none)'}\n"
        )

    def _parse(self, raw: str, corpus: Corpus) -> tuple[Proposal, ...]:
        obj = _extract_json(raw)
        if obj is None:
            return ()
        existing_ids = set(corpus.by_id().keys())
        out: list[Proposal] = []
        seen: set[str] = set()
        proposals = obj.get("proposals")
        if not isinstance(proposals, list):
            return ()  # absent/null/non-list -> no proposals (degrade, don't crash)
        for p in proposals:
            try:
                claim = self._build_claim(p)
            except (KeyError, ValueError, TypeError, FileNotFoundError):
                continue
            if claim.id in existing_ids or claim.id in seen:
                continue
            seen.add(claim.id)
            out.append(Proposal(operator_id=self.identity, claim=claim))
            if len(out) >= self.max_proposals:
                break
        return tuple(out)

    def _build_claim(self, p: dict):
        kind = str(p["kind"]).strip()
        if kind == "region_delta_beta":
            return self._build_region_claim(p)
        if kind == "n_dmps":
            return self._build_ndmp_claim(p)
        raise ValueError("bad methylation proposal kind")

    def _common(self, p: dict) -> tuple[str, str, str, str, str, Comparator, str | None]:
        title = str(p["title"]).strip()
        ref = str(p["ref"]).strip()
        group_col = str(p.get("group_col", "Sample_Group")).strip()
        level_a = str(p["level_a"]).strip()
        level_b = str(p["level_b"]).strip()
        cmp_key = str(p["comparator"]).strip().lower()
        if cmp_key not in _COMPARATORS:
            raise ValueError("bad comparator")
        if not (title and ref and group_col and level_a and level_b):
            raise ValueError("empty required field")
        if level_a == level_b:
            raise ValueError("levels must differ")
        self._validate_contract(ref, group_col, level_a, level_b)
        rationale = str(p["rationale"]).strip() if p.get("rationale") else None
        return title, ref, group_col, level_a, level_b, _COMPARATORS[cmp_key], rationale

    def _build_region_claim(self, p: dict):
        from .analysis_profile import profile_oracle_id
        from .methyl_adapters import region_delta_beta_claim
        from .profiles import CANONICAL_HM450_V1

        title, ref, group_col, level_a, level_b, comparator, rationale = self._common(p)
        probes = tuple(str(x).strip() for x in p["region_probes"] if str(x).strip())
        if not probes:
            raise ValueError("region_delta_beta requires region_probes")
        self._validate_probes(ref, probes)
        threshold = float(p["threshold"])
        cid = _METHYL_REGION_PREFIX + hashlib.sha256(
            f"{title}|{ref}|{','.join(probes)}|{group_col}|{level_a}|{level_b}|{comparator.value}|{threshold}".encode()
        ).hexdigest()[:16]
        claim = region_delta_beta_claim(
            cid,
            ref=ref,
            region_probes=probes,
            group_col=group_col,
            level_a=level_a,
            level_b=level_b,
            comparator=comparator,
            threshold=threshold,
            oracle_ref=profile_oracle_id(CANONICAL_HM450_V1) if "tcga_laml" in ref else None,
            title=title,
        )
        return self._with_generated_provenance(claim, rationale)

    def _build_ndmp_claim(self, p: dict):
        from .analysis_profile import profile_oracle_id
        from .methyl_ndmp import n_dmps_claim
        from .profiles import CANONICAL_HM450_V1

        title, ref, group_col, level_a, level_b, comparator, rationale = self._common(p)
        alpha = float(p["alpha"])
        k = float(p["k"])
        if not (0.0 < alpha < 1.0):
            raise ValueError("alpha must be in (0,1)")
        cid = _METHYL_NDMP_PREFIX + hashlib.sha256(
            f"{title}|{ref}|{group_col}|{level_a}|{level_b}|{alpha}|{k}|{comparator.value}".encode()
        ).hexdigest()[:16]
        claim = n_dmps_claim(
            cid,
            ref=ref,
            group_col=group_col,
            level_a=level_a,
            level_b=level_b,
            alpha=alpha,
            k=k,
            comparator=comparator,
            oracle_ref=profile_oracle_id(CANONICAL_HM450_V1) if "tcga_laml" in ref else None,
            title=title,
        )
        return self._with_generated_provenance(claim, rationale)

    def _with_generated_provenance(self, claim, rationale: str | None):
        return claim.model_copy(
            update={
                "provenance": Provenance(
                    generated_by=GenerationMode.AGENT_GENERATED,
                    agent_id=self.identity,
                    search_cardinality=1,
                    rationale=rationale,
                )
            }
        )

    @staticmethod
    def _validate_contract(ref: str, group_col: str, level_a: str, level_b: str) -> None:
        from .contracts import load_contract

        se = load_contract(ref)
        from pathlib import Path

        betas_path = Path(se.access_methods[0].access_url)
        manifest = json.loads((betas_path.parent / f"{se.contract_uid.split('@')[0]}.json").read_text())
        levels = {c[group_col] for c in manifest["col_data"]}
        if level_a not in levels or level_b not in levels:
            raise ValueError("unknown group level")

    @staticmethod
    def _validate_probes(ref: str, probes: tuple[str, ...]) -> None:
        from .methyl_ndmp import _all_probe_ids

        available = set(_all_probe_ids(ref))
        missing = [p for p in probes if p not in available]
        if missing:
            raise ValueError("unknown region probe")

    @classmethod
    def anthropic(
        cls,
        *,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        **kw,
    ) -> "MethylGenerationAdapter":
        """Build a methylation adapter backed by the Anthropic SDK (needs the [llm] extra)."""
        try:
            import anthropic
        except ModuleNotFoundError as e:  # pragma: no cover - exercised via CLI, not unit tests
            raise RuntimeError(
                "the methylation LLM adapter needs the optional extra: pip install 'polymer-claims[llm]'"
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
