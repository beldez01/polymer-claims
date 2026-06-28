"""Capability cell — a versioned descriptor of an executable claim capability
(spec 2026-06-27-capability-cell-design.md). Pure / numpy-free: grammar + stdlib only."""
from __future__ import annotations

import math
import re
from enum import Enum
from typing import Literal

from pydantic import computed_field, model_validator

from .base import _Model
from .claim import Claim
from .operations import (
    Comparator,
    ComputeGraph,
    DataHandle,
    EvaluationPlan,
    OperationNode,
    ProducedLeafSpec,
    SatisfactionCriterion,
)
from .pattern import PatternRef

_SE_CONTRACT_RE = re.compile(r"^se:[^:@\s]+@[0-9]+$")

SubjectKind = Literal[
    "genomic_region", "ontology_term", "variant_vrs", "s4_object", "gene_or_protein",
    "phenopacket", "pathway", "cohort", "literal", "composite",
]


class ParamCodec(_Model):
    name: str
    codec: Literal["string", "int", "float", "csv", "enum"]
    required: bool = True
    choices: tuple[str, ...] | None = None

    @model_validator(mode="after")
    def _check(self) -> ParamCodec:
        if not self.name.strip():
            raise ValueError("ParamCodec.name must be nonempty")
        if self.codec == "enum":
            if not self.choices or len(set(self.choices)) != len(self.choices):
                raise ValueError("enum codec requires nonempty unique choices")
            if any(not c.strip() for c in self.choices):
                raise ValueError("enum choices must be nonempty values")
        elif self.choices is not None:
            raise ValueError("non-enum codec must not set choices")
        return self

    def canonicalize(self, value: str) -> str:
        if self.codec == "string":
            return value
        if self.codec == "int":
            return str(int(value))
        if self.codec == "float":
            fv = float(value)
            if not math.isfinite(fv):
                raise ValueError("non-finite float")
            return repr(fv)
        if self.codec == "csv":
            toks = value.split(",")
            if any(t == "" or t != t.strip() for t in toks):
                raise ValueError("malformed csv")
            return ",".join(toks)
        if self.codec == "enum":
            if value not in (self.choices or ()):
                raise ValueError("not in choices")
            return value
        raise ValueError(f"unknown codec {self.codec}")  # pragma: no cover

    def is_canonical(self, value: str) -> bool:
        try:
            return self.canonicalize(value) == value
        except (ValueError, OverflowError):
            return False


class DataRefKind(str, Enum):
    OPAQUE = "opaque"
    SE_CONTRACT = "se_contract"


def data_ref_ok(kind: DataRefKind, ref: str) -> bool:
    if kind == DataRefKind.OPAQUE:
        return bool(ref)
    if kind == DataRefKind.SE_CONTRACT:
        return bool(_SE_CONTRACT_RE.match(ref))
    return False  # pragma: no cover


class SubjectRequirement(_Model):
    mode: Literal["forbidden", "optional", "required"]
    kind: SubjectKind | None = None

    @model_validator(mode="after")
    def _check(self) -> SubjectRequirement:
        if self.mode == "forbidden" and self.kind is not None:
            raise ValueError("forbidden subject must not set a kind")
        return self


class OracleRequirement(_Model):
    default_oracle_id: str | None = None
    required: bool = False

    @model_validator(mode="after")
    def _check(self) -> OracleRequirement:
        if self.default_oracle_id is not None and not self.default_oracle_id.strip():
            raise ValueError("default_oracle_id must be nonempty when set")
        return self


class CapabilityCell(_Model):
    capability_id: str
    capability_version: str
    operation_impl: str
    title: str
    pattern: PatternRef
    subject: SubjectRequirement
    param_schema: tuple[ParamCodec, ...]
    produced: ProducedLeafSpec
    allowed_comparators: tuple[Comparator, ...]
    eligible_adapter_identities: tuple[str, ...]
    min_executing_adapters: int = 2
    oracle: OracleRequirement
    data_ref_kind: DataRefKind
    claim_leaf_kinds: tuple[Literal["quantity", "categorical", "existence", "proposition"], ...]
    criterion_target: Literal["threshold", "reference_leaf", "either"]

    @property
    def ref(self) -> str:
        return f"{self.capability_id}@{self.capability_version}"

    @model_validator(mode="after")
    def _check(self) -> CapabilityCell:
        for s in (self.capability_id, self.capability_version, self.operation_impl, self.title):
            if not s.strip():
                raise ValueError("capability_id/version/operation_impl/title must be nonempty")
        names = [p.name for p in self.param_schema]
        if len(set(names)) != len(names):
            raise ValueError("param_schema names must be unique")
        if not self.allowed_comparators or len(set(self.allowed_comparators)) != len(self.allowed_comparators):
            raise ValueError("allowed_comparators must be nonempty and unique")
        ids = self.eligible_adapter_identities
        if len(set(ids)) != len(ids) or any(not i.strip() for i in ids):
            raise ValueError("eligible_adapter_identities must be unique and nonempty")
        if self.min_executing_adapters != 2:
            raise ValueError("V1: min_executing_adapters must be 2")
        if self.min_executing_adapters > len(ids):
            raise ValueError("min_executing_adapters exceeds eligible identities")
        if not self.claim_leaf_kinds:
            raise ValueError("claim_leaf_kinds must be nonempty")
        return self


class CapabilityRegistry(_Model):
    cells: tuple[CapabilityCell, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> CapabilityRegistry:
        keys = [(c.capability_id, c.capability_version) for c in self.cells]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate (capability_id, capability_version)")
        return self

    def resolve(self, capability_id: str, capability_version: str) -> CapabilityCell | None:
        for c in self.cells:
            if c.capability_id == capability_id and c.capability_version == capability_version:
                return c
        return None

    @property
    def is_empty(self) -> bool:
        return not self.cells


class ConformanceReason(str, Enum):
    CAPABILITY_NOT_REGISTERED = "capability_not_registered"
    OPERATION_IMPL_MISMATCH = "operation_impl_mismatch"
    PATTERN_MISMATCH = "pattern_mismatch"
    GRAPH_SHAPE_MISMATCH = "graph_shape_mismatch"
    PARAM_MISSING = "param_missing"
    PARAM_UNKNOWN = "param_unknown"
    PARAM_DUPLICATE = "param_duplicate"
    PARAM_MALFORMED = "param_malformed"
    OUTPUT_TYPE_MISMATCH = "output_type_mismatch"
    LEAF_SHAPE_MISMATCH = "leaf_shape_mismatch"
    COMPARATOR_NOT_ALLOWED = "comparator_not_allowed"
    CRITERION_TARGET_MISMATCH = "criterion_target_mismatch"
    SUBJECT_FORBIDDEN_PRESENT = "subject_forbidden_present"
    SUBJECT_REQUIRED_MISSING = "subject_required_missing"
    SUBJECT_KIND_MISMATCH = "subject_kind_mismatch"
    DATA_REF_KIND_MISMATCH = "data_ref_kind_mismatch"
    ORACLE_REQUIRED_MISSING = "oracle_required_missing"
    BINDING_NO_INDEPENDENT_PAIR = "binding_no_independent_pair"
    BINDING_ORACLE_MISSING = "binding_oracle_missing"


class ConformanceWarning(str, Enum):
    BINDING_ADAPTER_UNTRUSTED = "binding_adapter_untrusted"
    BINDING_ADAPTER_MISSING = "binding_adapter_missing"
    BINDING_ORACLE_SATISFIABILITY_UNKNOWN = "binding_oracle_satisfiability_unknown"


class ConformanceResult(_Model):
    reasons: tuple[ConformanceReason, ...] = ()
    warnings: tuple[ConformanceWarning, ...] = ()
    detail: str = ""

    @computed_field  # serialized yet derived — never separately stored
    @property
    def ok(self) -> bool:
        return not self.reasons


class CapabilityParamError(ValueError):
    """Raised by build_evaluation_plan on programmer misuse (bad params/comparator/oracle/data_ref)."""


def _dedup(items):
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return tuple(out)


def criterion_target_ok(target: str, criterion: SatisfactionCriterion) -> bool:
    has_threshold = criterion.threshold is not None
    has_ref = criterion.reference_leaf_index is not None
    if target == "threshold":
        return has_threshold and not has_ref
    if target == "reference_leaf":
        return has_ref and not has_threshold
    return has_threshold ^ has_ref  # "either": exactly one


def build_evaluation_plan(
    cell: CapabilityCell, *, params: dict[str, str], data_ref: str,
    criterion: SatisfactionCriterion, oracle_ref: str | None = None,
) -> EvaluationPlan:
    schema = {p.name: p for p in cell.param_schema}
    missing = [p.name for p in cell.param_schema if p.required and p.name not in params]
    if missing:
        raise CapabilityParamError(f"missing required params: {missing}")
    unknown = [k for k in params if k not in schema]
    if unknown:
        raise CapabilityParamError(f"unknown params: {unknown}")
    for k, v in params.items():
        if not schema[k].is_canonical(v):
            raise CapabilityParamError(f"param {k!r}={v!r} not canonical for codec {schema[k].codec}")
    if criterion.comparator not in cell.allowed_comparators:
        raise CapabilityParamError(f"comparator {criterion.comparator} not allowed")
    if not criterion_target_ok(cell.criterion_target, criterion):
        raise CapabilityParamError("criterion target shape not allowed")
    if not data_ref_ok(cell.data_ref_kind, data_ref):
        raise CapabilityParamError(f"data_ref {data_ref!r} invalid for {cell.data_ref_kind}")
    resolved = oracle_ref if oracle_ref is not None else cell.oracle.default_oracle_id
    if cell.oracle.required and resolved is None:
        raise CapabilityParamError("oracle required but none resolved")
    ordered = tuple((p.name, params[p.name]) for p in cell.param_schema if p.name in params)
    node = OperationNode(id="n0", impl=cell.operation_impl, inputs=(DataHandle(ref=data_ref),),
                         params=ordered, oracle_ref=resolved, produces=cell.produced)
    return EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="n0"), criterion=criterion)


def _subject_reasons(req: SubjectRequirement, subject):
    if req.mode == "forbidden":
        return [ConformanceReason.SUBJECT_FORBIDDEN_PRESENT] if subject is not None else []
    if subject is None:
        return [ConformanceReason.SUBJECT_REQUIRED_MISSING] if req.mode == "required" else []
    if req.kind is not None and subject.kind != req.kind:
        return [ConformanceReason.SUBJECT_KIND_MISMATCH]
    return []


def validate_claim_shape(claim: Claim, cell: CapabilityCell) -> ConformanceResult:
    reasons: list[ConformanceReason] = []
    plan = claim.evaluation_plan
    node = None
    if plan is None or len(plan.graph.nodes) != 1:
        reasons.append(ConformanceReason.GRAPH_SHAPE_MISMATCH)
    else:
        node = plan.graph.nodes[0]
        if node.id != "n0" or plan.graph.terminal != node.id:
            reasons.append(ConformanceReason.GRAPH_SHAPE_MISMATCH)
    # claim-level checks (independent of the node)
    if claim.pattern != cell.pattern:
        reasons.append(ConformanceReason.PATTERN_MISMATCH)
    if tuple(leaf.kind for leaf in claim.leaves) != tuple(cell.claim_leaf_kinds):
        reasons.append(ConformanceReason.LEAF_SHAPE_MISMATCH)
    reasons.extend(_subject_reasons(cell.subject, claim.subject))
    if plan is not None:
        if not criterion_target_ok(cell.criterion_target, plan.criterion):
            reasons.append(ConformanceReason.CRITERION_TARGET_MISMATCH)
        if plan.criterion.comparator not in cell.allowed_comparators:
            reasons.append(ConformanceReason.COMPARATOR_NOT_ALLOWED)
    # node-dependent checks
    if node is not None:
        data_input = (node.inputs[0]
                      if len(node.inputs) == 1 and isinstance(node.inputs[0], DataHandle) else None)
        if data_input is None:
            reasons.append(ConformanceReason.GRAPH_SHAPE_MISMATCH)
        if node.impl != cell.operation_impl:
            reasons.append(ConformanceReason.OPERATION_IMPL_MISMATCH)
        if node.produces != cell.produced:
            reasons.append(ConformanceReason.OUTPUT_TYPE_MISMATCH)
        keys = [k for k, _ in node.params]
        schema = {p.name: p for p in cell.param_schema}
        if len(keys) != len(set(keys)):
            reasons.append(ConformanceReason.PARAM_DUPLICATE)
        if any(p.required and p.name not in keys for p in cell.param_schema):
            reasons.append(ConformanceReason.PARAM_MISSING)
        for k, v in node.params:
            if k not in schema:
                reasons.append(ConformanceReason.PARAM_UNKNOWN)
            elif not schema[k].is_canonical(v):
                reasons.append(ConformanceReason.PARAM_MALFORMED)
        if data_input is not None and not data_ref_ok(cell.data_ref_kind, data_input.ref):
            reasons.append(ConformanceReason.DATA_REF_KIND_MISMATCH)
        if cell.oracle.required and node.oracle_ref is None:
            reasons.append(ConformanceReason.ORACLE_REQUIRED_MISSING)
    return ConformanceResult(reasons=_dedup(reasons))


def validate_claim_conformance(claim, registry, capability_id, capability_version) -> ConformanceResult:
    cell = registry.resolve(capability_id, capability_version)
    if cell is None:
        return ConformanceResult(reasons=(ConformanceReason.CAPABILITY_NOT_REGISTERED,),
                                 detail=f"{capability_id}@{capability_version} not registered")
    return validate_claim_shape(claim, cell)
