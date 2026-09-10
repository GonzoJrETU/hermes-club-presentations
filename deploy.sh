#!/usr/bin/env bash
# Build the deployable dist/ from the public decks, gate it, then deploy to Azure SWA.
# Usage: bash deploy.sh [--build-only]
#
# The gate (gate.py) is a HARD GATE: if any forbidden token survives in a public
# page, the build exits non-zero and nothing is deployed.
#
# Content REWRITING (replacing names with generic descriptors) needs the tokens in
# plaintext, so those scrubbers deliberately live OUTSIDE this public repo - see
# README "Privacy / PII policy". The decks stored here are already the scrubbed
# copies; point DECK_TOOLS at the local tools dir when you edit a raw working deck.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP_NAME=${APP_NAME:-hermes-at-home-walkthrough}
RG=${RG:-fsai-hermes-home}
TOOLS="${DECK_TOOLS:-}"

PY=python3; command -v "$PY" >/dev/null 2>&1 || PY=python; command -v "$PY" >/dev/null 2>&1 || PY=py

# Work with RELATIVE paths for every native tool call: in Git-Bash an absolute
# /tmp-style path passed as an argument can get rewritten and break the call.
cd "$ROOT"

# 1. (re)build dist
rm -rf dist
mkdir -p dist
cp favicon.svg favicon.ico favicon.png dist/ 2>/dev/null || true

# page copies: source page -> public URL path
cp hermes-at-home-walkthrough.html         dist/index.html
cp your-second-brain.html                  dist/second-brain.html
cp research-framework.html                 dist/research-framework.html
cp speaker-notes-hermes-at-home.html       dist/speaker-notes-hermes-at-home.html
cp speaker-notes-research-framework.html   dist/speaker-notes-research-framework.html

# 2. optional content rewrite (local tools only — they hold the plaintext tokens)
if [ -n "$TOOLS" ] && [ -d "$TOOLS" ]; then
  DISTW="$(cygpath -w "$ROOT/dist" 2>/dev/null || echo "$ROOT/dist")"
  echo "Rewriting content with local tools from: $TOOLS"
  [ -f "$TOOLS/scrub_index.py" ]              && "$PY" "$TOOLS/scrub_index.py" "$DISTW/index.html"
  [ -f "$TOOLS/scrub_research_framework.py" ] && "$PY" "$TOOLS/scrub_research_framework.py" \
        "$DISTW/research-framework.html" "$DISTW/speaker-notes-research-framework.html"
  true
else
  echo "note: DECK_TOOLS not set — skipping content rewrite (stored decks are already scrubbed)"
fi

# 3. gate the whole bundle
"$PY" gate.py dist

echo "Built dist/: index.html + second-brain.html + research-framework.html + 2 speaker-notes pages"

if [ "${1:-}" = "--build-only" ]; then
  echo "Build complete (deploy skipped)."
  exit 0
fi

# 4. deploy via the native StaticSitesClient (reliable on Windows)
if ! command -v az >/dev/null 2>&1; then echo "az not found"; exit 1; fi
TOKEN=$(az staticwebapp secrets list -n "$APP_NAME" -g "$RG" --query properties.apiKey -o tsv)
CLIENT=$(ls "$HOME/.swa/deploy/"*/StaticSitesClient.exe 2>/dev/null | head -1)
WINDIST="$(cygpath -w "$ROOT/dist" 2>/dev/null || echo "$ROOT/dist")"
if [ -z "$CLIENT" ]; then
  echo "StaticSitesClient not cached; run once via: swa deploy (it downloads the client)"
  exit 1
fi
echo "Deploying to $APP_NAME/$RG ..."
DEPLOYMENT_ACTION=upload DEPLOYMENT_PROVIDER=SwaCli SKIP_APP_BUILD=true \
SKIP_API_BUILD=true DEPLOYMENT_TOKEN="$TOKEN" APP_LOCATION="$WINDIST" \
VERBOSE=false "$CLIENT"
echo "Done."
