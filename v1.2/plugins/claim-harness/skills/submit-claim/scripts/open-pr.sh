#!/usr/bin/env bash
# open-pr.sh — submit a validated FormalClaim to github.com/beldez01/polymer-claims.
#
# Preconditions:
#   - `gh` CLI installed and `gh auth status` succeeds.
#   - `uvx polymer-formalclaim validate <path>` returned LICENSED.
#
# Arguments:
#   $1  path to the claim JSON file
#   $2  (optional) --slug <slug> to override the auto-derived slug
#   $3  (optional) --topic <topic> to override the auto-picked target domain
#
# Environment:
#   UPSTREAM  defaults to "beldez01/polymer-claims"
#   FORK      defaults to "<gh-user>/polymer-claims"

set -euo pipefail

CLAIM_PATH=${1:-}
if [[ -z "$CLAIM_PATH" || ! -f "$CLAIM_PATH" ]]; then
  echo "usage: open-pr.sh <claim.json> [--slug SLUG] [--topic TOPIC]" >&2
  exit 2
fi

shift
SLUG=""
TOPIC=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug)  SLUG="$2"; shift 2;;
    --topic) TOPIC="$2"; shift 2;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done

UPSTREAM="${UPSTREAM:-beldez01/polymer-claims}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install from https://cli.github.com and run \`gh auth login\`." >&2
  exit 3
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "gh not authenticated. Run \`gh auth login\` first." >&2
  exit 3
fi

GH_USER=$(gh api user -q .login)
FORK="${FORK:-$GH_USER/polymer-claims}"

# Belt-and-suspenders: re-validate locally.
echo "Re-validating $CLAIM_PATH…"
uvx --from "polymer-formalclaim>=0.2.0" polymer-formalclaim validate "$CLAIM_PATH"

# Pick a slug.
if [[ -z "$SLUG" ]]; then
  SLUG=$(python - <<PY
import json, re, sys
d = json.load(open("$CLAIM_PATH"))
title = d.get("title", "untitled")
slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:60]
print(slug or "claim")
PY
)
fi

# Pick a topic.
if [[ -z "$TOPIC" ]]; then
  TOPIC=$(python - <<PY
import json
d = json.load(open("$CLAIM_PATH"))
dom = d.get("domain", "other")
subj_kind = (d.get("subject") or {}).get("kind", "")
title = (d.get("title","") + " " + (d.get("subject",{}) or {}).get("display","")).lower()
if "hla" in title:
    print("hla")
elif "recomb" in title or "crossover" in title or "hotspot" in title:
    print("recombination_hotspots")
elif "te " in title or "transposable" in title or "retro" in title or "sine" in title or "ltr" in title:
    print("te_surveillance")
elif "dual" in title or "cost" in title or "expression" in title:
    print("dual_channel")
elif dom == "clinical":
    print("clinical")
elif dom == "single_cell":
    print("single_cell")
else:
    print("other")
PY
)
fi
echo "Target: corpus/domains/$TOPIC/claims/$SLUG.json"

# Prepare working clone under a temp path.
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Ensure fork exists.
if ! gh repo view "$FORK" >/dev/null 2>&1; then
  echo "Forking $UPSTREAM → $FORK…"
  gh repo fork "$UPSTREAM" --clone=false
fi

cd "$TMPDIR"
gh repo clone "$FORK" .
git remote add upstream "https://github.com/$UPSTREAM.git" || true
git fetch upstream main
git checkout -B "submit/$SLUG" upstream/main

# Write the claim.
mkdir -p "corpus/domains/$TOPIC/claims"
cp "$CLAIM_PATH" "corpus/domains/$TOPIC/claims/$SLUG.json"

git add "corpus/domains/$TOPIC/claims/$SLUG.json"
git -c user.name="$GH_USER" -c user.email="$GH_USER@users.noreply.github.com" \
  commit -m "add: $TOPIC/$SLUG"

git push --force-with-lease origin "submit/$SLUG"

# Build PR body.
BODY=$(cat <<EOF
## Claim submission

Submitted by the Polymer Claims harness (\`$GH_USER\`).

**Slug:** \`$TOPIC/$SLUG\`
**Local verdict:** LICENSED
**Harness version:** $(uvx --from "polymer-formalclaim>=0.2.0" polymer-formalclaim --version 2>/dev/null || echo "unknown")

See \`CONTRIBUTING.md\` for the review process.
EOF
)

gh pr create \
  --repo "$UPSTREAM" \
  --base main \
  --head "$GH_USER:submit/$SLUG" \
  --title "add: $TOPIC/$SLUG" \
  --body "$BODY"

echo "✓ PR opened."
