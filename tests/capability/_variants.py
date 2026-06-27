"""Shared builder variant matrices + canonical snapshot form. Plain module (no package):
pytest prepend-mode puts this dir on sys.path; the capture script inserts it explicitly."""
from polymer_claims.exec_adapters import mean_diff_claim
from polymer_claims.methyl_adapters import region_delta_beta_claim
from polymer_claims.methyl_ndmp import n_dmps_claim
from polymer_grammar.operations import Comparator
from polymer_grammar.strength import StrengthVector

# One shared, valid 6-axis strength vector (each axis in [0,1], higher-is-better).
STRENGTH = StrengthVector(
    magnitude=0.5, certainty=0.5, evidence_against_null=0.5,
    severity=0.5, world_contact=0.5, explanatory_virtue=0.5,
)

MEAN_DIFF_VARIANTS = [
    ("default", mean_diff_claim, {"claim_id": "md-default"}),
    ("cmp_lt", mean_diff_claim, {"claim_id": "md-lt", "comparator": Comparator.LT, "threshold": 3.5}),
    ("cmp_eq", mean_diff_claim, {"claim_id": "md-eq", "comparator": Comparator.EQ, "threshold": 2.0}),
    ("cmp_ne", mean_diff_claim, {"claim_id": "md-ne", "comparator": Comparator.NE, "threshold": 2.0}),
    ("alt_oracle", mean_diff_claim, {"claim_id": "md-oracle", "oracle_ref": "other_apparatus"}),
    ("rationale", mean_diff_claim, {"claim_id": "md-rat", "rationale": "agent said so"}),
    ("strength", mean_diff_claim, {"claim_id": "md-str", "strength": STRENGTH}),
    ("custom_title_term", mean_diff_claim,
     {"claim_id": "md-t", "title": "X vs Y", "ontology_term": "custom-term"}),
]
REGION_VARIANTS = [
    ("default", region_delta_beta_claim, {"claim_id": "rg-default"}),
    ("cmp_lt", region_delta_beta_claim, {"claim_id": "rg-lt", "comparator": Comparator.LT, "threshold": 0.2}),
    ("cmp_eq", region_delta_beta_claim, {"claim_id": "rg-eq", "comparator": Comparator.EQ, "threshold": 0.1}),
    ("cmp_ne", region_delta_beta_claim, {"claim_id": "rg-ne", "comparator": Comparator.NE, "threshold": 0.1}),
    ("alt_oracle", region_delta_beta_claim, {"claim_id": "rg-oracle", "oracle_ref": "other_apparatus"}),
    ("missing_subject", region_delta_beta_claim, {"claim_id": "rg-nosub", "with_subject": False}),
    ("strength", region_delta_beta_claim, {"claim_id": "rg-str", "strength": STRENGTH}),
    ("custom_region_title", region_delta_beta_claim,
     {"claim_id": "rg-reg", "region": ("chr2", 50, 999), "title": "T", "ontology_term": "ot"}),
]
NDMP_VARIANTS = [
    ("default_probe_resolution", n_dmps_claim, {"claim_id": "nd-default", "k": 5.0}),
    ("explicit_probes", n_dmps_claim, {"claim_id": "nd-probes", "k": 5.0, "probes": ("cg1", "cg2", "cg3")}),
    ("cmp_gt", n_dmps_claim, {"claim_id": "nd-gt", "k": 7.0, "comparator": Comparator.GT}),
    ("cmp_eq", n_dmps_claim, {"claim_id": "nd-eq", "k": 5.0, "comparator": Comparator.EQ}),
    ("cmp_ne", n_dmps_claim, {"claim_id": "nd-ne", "k": 5.0, "comparator": Comparator.NE}),
    ("alt_oracle", n_dmps_claim, {"claim_id": "nd-oracle", "k": 5.0, "oracle_ref": "other_apparatus"}),
    ("strength", n_dmps_claim, {"claim_id": "nd-str", "k": 5.0, "strength": STRENGTH}),
    ("custom_region", n_dmps_claim, {"claim_id": "nd-reg", "k": 5.0, "region": ("chr3", 1, 100)}),
]
ALL_VARIANTS = {"mean_diff": MEAN_DIFF_VARIANTS, "region": REGION_VARIANTS, "n_dmps": NDMP_VARIANTS}


def canonical_form(claim) -> dict:
    plan = claim.evaluation_plan
    return {"claim_json": claim.model_dump_json(),
            "graph_hash": plan.graph.content_hash if plan else None}
