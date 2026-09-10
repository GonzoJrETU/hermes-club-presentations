# Hermes Club Presentations — buildable source

This repo is the **single buildable source** for the public Hermes implementation
presentation decks that are hosted on Azure Static Web Apps. If the Azure resources
are ever cleaned up, any of these pages can be rebuilt and redeployed from exactly
what's here — nothing is lost.

## What's in this repo

| File | What it is |
|------|------------|
| `hermes-at-home-walkthrough.html` | "Hermes at Home" — the interactive walkthrough deck (13 sections, self-contained D3 force graph, live terminal demo). Single presenter voice, medium-technical audience. |
| `your-second-brain.html` | "Your Second Brain" — follow-up deck: second-brain anatomy, methods (PARA / Zettelkasten / LLM-Wiki), GBrain vs Open Brain (OB1), build-your-own path. |
| `research-framework.html` | "The Research Framework" — deep-dive deck: request → intake → named-board routing → shared harvest cache → how every source is described/graded → freshness windows → the mandatory landing sequence → retrieval → guardrails. Clickable 10-stage pipeline, routing-decision demo, source explorer with live filter, cache toggle, harvest-CLI replay. |
| `speaker-notes-hermes-at-home.html` | Print-friendly speaker-notes companion for deck #1 (talking cues + 45-min timing flow). |
| `speaker-notes-research-framework.html` | Print-friendly speaker-notes companion for deck #3 (12 sections, 41-min timing flow, key facts, likely Q&A with honest answers). |
| `gate.py` | **The PII gate.** Hash-based (stored as digests, no plaintext word list) — fails the build if a forbidden token appears in `dist/`. |
| `deploy.sh` / `deploy.ps1` | Build `dist/`, run the gate, deploy to Azure SWA. Content-rewriting scrubbers live outside this repo (see Privacy). |
| `favicon.svg` (+ `.ico`/`.png`) | Icon used by the decks. |

All decks are **self-contained** — D3 and every asset are inlined, so they run
offline from `file://` and deploy as static HTML with zero build step beyond
copying files.

> **The files stored here are already the PUBLIC (scrubbed) copies** — same as
> `index.html` is. `deploy.sh` runs the hash gate on `dist/` before deploying, so a
> raw working deck fails the build instead of shipping.
> Keep editing the raw decks in the local FamilyStewardAI guide; copy the scrubbed
> output here.

## Quick start (view locally)

Open any `.html` file in a browser directly — they're static and need nothing.

```bash
# or serve them locally
python -m http.server 8080
# → http://localhost:8080/hermes-at-home-walkthrough.html
```

## Rebuild the deployable bundle

```bash
# The dist/ folder is what goes to Azure. Today it's just a copy of the decks
# renamed to the Azure paths; regenerate with:
mkdir -p dist
cp favicon.svg favicon.ico favicon.png dist/
cp hermes-at-home-walkthrough.html dist/index.html
cp your-second-brain.html dist/second-brain.html
```
...or just run `bash deploy.sh --build-only`, which does the copies **and** the
PII gate in one step (preferred — the gate is what keeps the public copy clean).

That's it — the decks carry their own styling, scripts, and the D3 force graph
inline, so `dist/` needs no bundling. The `./dist ` output is the deploy source.

## Deploy to Azure Static Web Apps (Free)

The sites run on Azure Static Web Apps (free tier). There are **two ways** to
deploy, both documented because the CLI wrapper has a known quirk on Windows.

### Prerequisites
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az`), logged in: `az login`
- [SWA CLI](https://azure.github.io/static-web-apps-cli/) (`swa`) — optional; see below
- The existing static web app resource (see "Where it lives" below)

### Method A — native deploy client (reliable on Windows, preferred)

The `swa` CLI wrapper on this box mis-resolves the output location and masks the
real error. The reliable path is the native `StaticSitesClient.exe` that the CLI
downloads, driven by environment variables:

```bash
# Get the deploy token for the site (never commit or print it)
TOKEN=$(az staticwebapp secrets list \
  -n hermes-at-home-walkthrough \
  -g fsai-hermes-home \
  --query properties.apiKey -o tsv)

# Locate the native client the SWA CLI cached
CLIENT=$(ls ~/.swa/deploy/*/StaticSitesClient.exe | head -1)

# Deploy the dist/ folder (env-driven)
DEPLOYMENT_ACTION=upload \
DEPLOYMENT_PROVIDER=SwaCli \
SKIP_APP_BUILD=true \
SKIP_API_BUILD=true \
DEPLOYMENT_TOKEN="$TOKEN" \
APP_LOCATION="$PWD/dist" \
VERBOSE=false \
"$CLIENT"
```

The client prints `Deployment Complete` and the live URL on success.

### Method B — SWA CLI (simplest, but path quirk on Windows)

```bash
TOKEN=$(az staticwebapp secrets list -n hermes-at-home-walkthrough -g fsai-hermes-home --query properties.apiKey -o tsv)
SWA_CLI_DEPLOYMENT_TOKEN="$TOKEN" swa deploy ./dist --env production --no-use-keychain --clear-credentials
```

> **Windows quirk:** `swa deploy` computes `APP_LOCATION` relative to a stored
> config and has produced `Deployment failed with exit code 1` even when upload
> would succeed. If that happens, use Method A (native client) — it deploys the
> exact same bundle reliably.

## Where it lives (Azure)

| Page | Live path | Azure resource |
|------|-----------|----------------|
| Hermes at Home | `https://<host>/` | Static web app `hermes-at-home-walkthrough` (Free) · resource group `fsai-hermes-home` |
| Your Second Brain | `https://<host>/second-brain.html` | same app |
| The Research Framework | `https://<host>/research-framework.html` | same app |
| Research Framework — speaker notes | `https://<host>/speaker-notes-research-framework.html` | same app |

> The app/resource group were deleted once to free the Free-tier site cap and are
> recreated by `deploy.sh` on demand; the hostname changes on recreation, so treat
> the table as *paths on whatever host `az staticwebapp show` reports*.

To recreate the app from scratch (only if the resource group is gone):

```bash
az group create -n fsai-hermes-home --location eastus2
az staticwebapp create -n hermes-at-home-walkthrough -g fsai-hermes-home \
  --sku Free --location eastus2 --output none
# then deploy ./dist per Method A above
```

> **Free-tier note:** this subscription already runs near the Azure **10-site Free
> SWA cap**, so new decks are added as *pages on the existing app* (`/second-brain.html`)
> rather than as new sites. Plan accordingly — if the cap blocks you, either free
> up a site or accept the existing host.

## Privacy / PII policy

These are **public** decks. They contain **no family names, no email addresses,
no phone numbers, no salary/retirement figures, and no venture-specific private
data.** They were deliberately scrubbed before making them public:

- Household members are referred to generically ("per-person", "household member").
- The health/product ventures are labeled by category (Health, Wellness, Comms…),
  not by brand story details — **including the graph node IDs**, which were renamed
  to match the generic labels (a bare codename in a JSON node is still a leak).
- The D3 force graph uses role-safe node labels.
- Named clinicians / creators / shows in the research deck are replaced by **role
  descriptors** ("bench-scientist lab podcast", "high-reach commercial health
  funnel"). Publishing a named real person as our "intel-only / commercial funnel"
  read is not something we ship, even when it is our honest internal assessment.

### The gate — and why this repo has no word list in it

`gate.py` fails the build (non-zero exit) if any forbidden token is present in
`dist/`. It stores only **SHA-256 digests** of the normalized tokens, matched
against the 1- and 2-word n-grams of each page, because a public plaintext
blocklist would itself publish the names it exists to keep out. Build logs mask
matches (`r***** p******`) for the same reason.

The scrubbers that *rewrite* content need the tokens in plaintext, so they are
**not** in this repo — they live with the authoring machine's local guide
(`FamilyStewardAI/docs/HERMES_IMPLEMENTATION_GUIDE/tools/`). A fresh clone already
contains the scrubbed decks, so the gate is all a rebuild needs:

```bash
# gate only
python gate.py dist

# full rebuild (gate always runs; set DECK_TOOLS to also re-apply the scrubbers)
DECK_TOOLS=/path/to/guide/tools bash deploy.sh --build-only
```

`deploy.sh` / `deploy.ps1` run the gate before the upload step, so a leak aborts
the build instead of reaching Azure.

**Also note:** the repo was recreated once to purge an earlier history whose raw
working decks contained household first names. Keep the stored files scrubbed —
cleaning the working tree does not clean git history.

## Loadable companion skill

The "build your own second brain" flow taught in `your-second-brain.html` is also
available as a Hermes skill: `second-brain-bootcamp` (in the presenter's own
profile skills dir, under `note-taking/second-brain-bootcamp/`).
It guides a new Hermes Desktop user through creating their own PARA-style second
brain (schema, index, log, templates, linking, optional local-only semantic layer).

## License

The presentation content in this repo is provided for sharing with the community
that attended the session. Built on Hermes Agent (Nous Research), MIT-licensed.