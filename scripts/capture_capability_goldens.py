"""ONE-TIME capture of frozen golden fixtures. Run BEFORE refactoring the builders.
DO NOT run after refactor — it would re-bless the current output. Overwrites are guarded."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "capability"))
from _variants import ALL_VARIANTS, canonical_form  # noqa: E402

GOLDEN = ROOT / "tests" / "capability" / "golden"


def main() -> None:
    GOLDEN.mkdir(parents=True, exist_ok=True)
    if any(GOLDEN.glob("*.json")):
        sys.exit("golden/ already populated; refusing to overwrite (delete deliberately to recapture)")
    for group, variants in ALL_VARIANTS.items():
        for name, builder, kwargs in variants:
            (GOLDEN / f"{group}__{name}.json").write_text(
                json.dumps(canonical_form(builder(**kwargs)), indent=2, sort_keys=True))
    print(f"captured {sum(len(v) for v in ALL_VARIANTS.values())} goldens")


if __name__ == "__main__":
    main()
